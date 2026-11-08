import os
import json
import math
import re
from ..models import Figures
from ..models import DanceFloor as DF
from .addon_utils import (
    END_FACING_NOTATIONS,
    duration_addon_bars,
    is_addon_array_noop,
    is_malformed_duration_addon,
    validate_addon_array_nulls,
    validate_end_facing_values,
)


class EndFacingError(ValueError):
    """A structured error raised when an EndFacing target cannot be resolved."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class SimpleFigure(Figures.Figure):
    _Partner = []
    _CriptDesc = []
    _Addons = []

    def __init__(self, loadFile, Anchor = [0,0], Addons = []):
        self.clear()
        self.name = loadFile
        self.Anchor = Anchor
        self.loadFigure(loadFile, Addons)

    def clear(self):
        super().clear()
        self._Partner = []
        self._CriptDesc = []
        self._Addons = []
        self._EndFacingPos = []
        self._StartFacingPos = []
        self._StartDancers = []

    @property
    def Bars(self):
        bars = super().Bars
        for addon in self._Addons:
            bars = addon.Bars(bars)
        return bars
    @Bars.setter
    def Bars(self, newBars):
        self._Bars = newBars

    @property
    def Desc(self):
        addDesc = ''
        for Addon in self._Addons:
            tmpDesc = Addon.Desc
            if len(tmpDesc) > 0:
                addDesc = addDesc + '\n' + tmpDesc

        if len(addDesc) > 0:
            return super().Desc + '\n' + addDesc
        else:
            return  super().Desc
    @Desc.setter
    def Desc(self, newDesc):
        self._Desc = newDesc

    @property
    def StartPos(self):
        tmpPos = super().StartPos
        for Addon in self._Addons:
            tmpPos = Addon.StartPos(tmpPos)
        return tmpPos
    @StartPos.setter
    def StartPos(self, newStartPos):
        self._StartPos = newStartPos

    @property
    def EndPos(self):
        tmpPos = super().EndPos
        for Addon in self._Addons:
            tmpPos = Addon.EndPos(tmpPos)
        return tmpPos
    @EndPos.setter
    def EndPos(self, newEndPos):
        self._EndPos = newEndPos

    @property
    def StartFacing(self):
        return self._StartFacingPos
    @StartFacing.setter
    def StartFacing(self, newFacing):
        self._StartFacingPos = newFacing

    @property
    def EndFacing(self):
        tmpPos = self._EndFacingPos
        for Addon in self._Addons:
            tmpPos = Addon.EndFacing(tmpPos)
        return tmpPos
    @EndFacing.setter
    def EndFacing(self, newFacing):
        self._EndFacingPos = newFacing

    @property
    def Partner(self):
        tmpPos = super().Partner
        for Addon in self._Addons:
            tmpPos = Addon.Partner(tmpPos)
        return tmpPos
    @Partner.setter
    def Partner(self, newPartner):
        self._Partner = newPartner

    def DanceMove(self, oldDF):
        newDF = DF.DanceFloor('dummy')
        newDF.AktBar = oldDF.AktBar + self.Bars

        for i in range(len(self.StartPos)):
            tmpStartPos = self.posWithAnchor(self.StartPos[i])
            tmpEndPos = self.posWithAnchor(self.EndPos[i])
            dancer = oldDF.DancerbyPos(tmpStartPos)
            tmpFacing = self.resolve_end_facing(
                i, oldDF, tmpStartPos, tmpEndPos, dancer
            )
            newDF.addDancer(dancer, tmpEndPos, tmpFacing)

        return newDF

    def resolve_end_facing(self, index, incoming_floor, start_position, end_position, dancer=None):
        """Resolve one outgoing facing to an absolute target using the actual floor."""
        facing_entries = self.EndFacing
        declaration = facing_entries[index] if index < len(facing_entries) else None
        is_implicit_default = declaration is None or declaration == "" or declaration == []
        if is_implicit_default:
            target = DF.default_facing_target(end_position)
        elif isinstance(declaration, (list, tuple)) and len(declaration) == 2:
            target = self.posWithAnchor(declaration)
        elif isinstance(declaration, str):
            if declaration == "M":
                raise EndFacingError(
                    "unsupported_facing_notation",
                    "EndFacing notation 'M' is explicitly unsupported because last-move direction is not available.",
                )
            if declaration not in END_FACING_NOTATIONS:
                raise EndFacingError(
                    "invalid_end_facing",
                    f"Unsupported EndFacing notation {declaration!r}.",
                )
            if declaration == "=":
                incoming_facing = incoming_floor.DanceFloorMap[start_position][1]
                if (
                    not isinstance(incoming_facing, (list, tuple))
                    or len(incoming_facing) != 2
                    or any(
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                        for value in incoming_facing
                    )
                    or tuple(incoming_facing) == tuple(start_position)
                ):
                    raise EndFacingError(
                        "invalid_incoming_facing",
                        f"EndFacing '=' requires a valid incoming facing target for dancer {index + 1}.",
                    )
                target = (
                    end_position[0] + incoming_facing[0] - start_position[0],
                    end_position[1] + incoming_facing[1] - start_position[1],
                )
            elif declaration in ("I", "O"):
                column = end_position[1]
                if column == 0:
                    raise EndFacingError(
                        "invalid_end_facing",
                        f"EndFacing {declaration!r} is undefined at absolute center column 0.",
                    )
                target = (
                    end_position[0],
                    0 if declaration == "I" else 2 * column,
                )
            elif declaration in ("U", "D"):
                target = (
                    end_position[0] - 1 if declaration == "U" else end_position[0] + 1,
                    end_position[1],
                )
            else:
                if dancer is None:
                    dancer = incoming_floor.DancerbyPos(start_position)
                gender = str(getattr(dancer, "gender", "")).lower()
                if gender.startswith("m"):
                    own_line = -1
                elif gender.startswith("f"):
                    own_line = 1
                else:
                    raise EndFacingError(
                        "invalid_dancer_identity",
                        f"EndFacing {declaration!r} requires a dancer with male or female identity.",
                    )
                target_line = own_line if declaration == "OwnL" else -own_line
                if end_position[1] == target_line:
                    raise EndFacingError(
                        "invalid_end_facing",
                        f"EndFacing {declaration!r} is undefined because dancer {index + 1} is already on target line {target_line}.",
                    )
                target = (end_position[0], target_line)
        else:
            raise EndFacingError(
                "invalid_end_facing",
                f"Invalid EndFacing declaration for dancer {index + 1}.",
            )

        if (
            not isinstance(target, (list, tuple))
            or len(target) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in target
            )
        ):
            raise EndFacingError(
                "invalid_end_facing",
                f"EndFacing for dancer {index + 1} resolved to an invalid target {target!r} from final position {end_position!r}.",
            )
        return target

    def getCrips(self, myDF):
        myCrips = []

        if not isinstance(myDF, DF.DanceFloor):
            raise Exception("Sorry, no Dance Floor")

        aktCrips = list(self._CriptDesc)
        for Addon in self._Addons:
            aktCrips = Addon.getCrips(aktCrips)

        if len(self.StartPos) != len(aktCrips):
            raise Exception("Sorry, no Cripts for everyone")

        for i in range(len(aktCrips)):
            myCript = str(aktCrips[i])
            if '{Dancer}' in myCript:
                myCript = myCript.replace('{Dancer}', myDF.DancerbyPos(self.posWithAnchor(self.StartPos[i])).name)

            if '{StartPos}' in myCript:
                myCript = myCript.replace('{StartPos}', myDF.PosNamebyPos(self.posWithAnchor(self.StartPos[i])))

            if '{EndPos}' in myCript:
                myCript = myCript.replace('{EndPos}', myDF.PosNamebyPos(self.posWithAnchor(self.EndPos[i])))

            if '{Face}' in myCript:
                start_position = self.posWithAnchor(self.StartPos[i])
                end_position = self.posWithAnchor(self.EndPos[i])
                dancer = myDF.DancerbyPos(start_position)
                target = self.resolve_end_facing(
                    i, myDF, start_position, end_position, dancer
                )
                face_name = myDF.PosNamebyPos(target)
                if not face_name:
                    face_name = f"position {tuple(target)}"
                myCript = myCript.replace('{Face}', face_name)

            if '{Partner}' in myCript:
                partner_position = self.Partner[i] if len(self.Partner) > i else ''
                # Some symmetric couple figures encode Partner as their own start
                # offset. In that case the adjacent dancer is the described partner.
                if (isinstance(partner_position, (list, tuple)) and i < len(self.StartPos)
                        and tuple(partner_position) == tuple(self.StartPos[i])
                        and i ^ 1 < len(self.StartPos)):
                    partner_position = self.StartPos[i ^ 1]
                if partner_position != '':
                    myCript = myCript.replace(
                        '{Partner}', myDF.DancerbyPos(self.posWithAnchor(partner_position)).name
                    )
                else:
                    raise Exception("Sorry, no partner!")
            if len(myCript) > 0:
                myCrips.append(str(myDF.AktBar) + ' - ' + str(myDF.AktBar+self.Bars-1) + ': ' + myCript)

        return myCrips

    def loadFigure(self, Filename, Addons):
        # Try both data/Figures and data/Dances directories
        paths_to_try = [
            os.path.join(os.getcwd(), 'data', 'Figures', Filename + '.json'),
            os.path.join(os.getcwd(), 'data', 'Dances', Filename + '.json'),
        ]
        
        fig_path = None
        for path in paths_to_try:
            if os.path.isfile(path):
                fig_path = path
                break
        
        if not fig_path:
            raise FileNotFoundError(f"Figure file not found: {Filename}.json in {', '.join(paths_to_try)}")
        
        with open(fig_path, 'r') as f:
            FigData = json.load(f)
        myKeys = FigData.keys()
        if 'Version' in myKeys:
            if FigData['Version'] != 2:
                raise Exception("Sorry, not the right file version")

        if 'Name' in myKeys:
            self.Name = FigData['Name']
        if 'Desc' in myKeys:
            self.Desc = FigData['Desc']
        if 'Bars' in myKeys:
            self.Bars = FigData['Bars']


        if 'StartPos' in myKeys:
            tmpList = []
            for i in range(len(FigData['StartPos'])):
                tmpList.append((FigData['StartPos'][i][0], FigData['StartPos'][i][1]))
            self.StartPos = tmpList
        if 'EndPos' in myKeys:
            tmpList = []
            for i in range(len(FigData['EndPos'])):
                tmpList.append((FigData['EndPos'][i][0], FigData['EndPos'][i][1]))
            self.EndPos = tmpList
        start_count = len(self.StartPos)
        start_dancers = FigData.get('StartDancers')
        if 'StartDancers' in FigData:
            if not isinstance(start_dancers, list) or len(start_dancers) != start_count:
                raise ValueError(
                    f"StartDancers must have the same length as StartPos ({start_count})."
                )
        else:
            start_dancers = [''] * start_count
        resolved_dancers = []
        for index, dancer_id in enumerate(start_dancers):
            if dancer_id == '':
                dancer_id = f"{index // 2 + 1}{'m' if index % 2 == 0 else 'w'}"
            elif not isinstance(dancer_id, str) or not re.fullmatch(r'[1-9][0-9]*[mw]', dancer_id):
                raise ValueError(
                    f"Invalid StartDancers identifier {dancer_id!r}; expected a couple number followed by 'm' or 'w'."
                )
            resolved_dancers.append(dancer_id)
        if len(set(resolved_dancers)) != len(resolved_dancers):
            duplicates = sorted({name for name in resolved_dancers if resolved_dancers.count(name) > 1})
            raise ValueError(
                f"StartDancers identifiers must be unique after automatic allocation; duplicate: {', '.join(duplicates)}."
            )
        self.StartDancers = resolved_dancers

        start_facing = FigData.get('StartFacing')
        if 'StartFacing' not in FigData:
            start_facing = [[] for _ in range(start_count)]
        if not isinstance(start_facing, list) or len(start_facing) != start_count:
            raise ValueError(
                f"StartFacing must have the same length as StartPos ({start_count})."
            )
        resolved_facing = []
        for index, target in enumerate(start_facing):
            if target == []:
                resolved_facing.append('')
                continue
            if (
                not isinstance(target, (list, tuple))
                or len(target) != 2
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    for value in target
                )
            ):
                raise ValueError(
                    f"Invalid StartFacing entry at index {index}; expected an empty entry or a finite target coordinate pair."
                )
            resolved_facing.append((target[0], target[1]))
        self.StartFacing = resolved_facing
        if 'CriptDesc' in myKeys:
            tmpList = []
            for i in range(len(FigData['CriptDesc'])):
                tmpList.append(FigData['CriptDesc'][i])
            self._CriptDesc = tmpList
        if 'Faceing' in myKeys:
            raise ValueError("Unsupported legacy figure key 'Faceing'; use 'EndFacing'.")
        addon_definitions = FigData.get('Addons', {})
        if not isinstance(addon_definitions, dict):
            raise ValueError("Figure Addons must be an object")
        for addon_name, addon_data in addon_definitions.items():
            if duration_addon_bars(addon_name) is not None:
                raise ValueError(
                    f"Figure addon {addon_name!r} uses the reserved B<n> duration addon name."
                )
            if isinstance(addon_data, dict):
                validate_addon_array_nulls(addon_name, addon_data)
                if 'EndFacing' in addon_data:
                    validate_end_facing_values(
                        addon_data['EndFacing'],
                        owner=f"Addon {addon_name!r} EndFacing",
                        allow_null=True,
                    )
            if isinstance(addon_data, dict) and 'Faceing' in addon_data:
                raise ValueError(
                    f"Unsupported legacy addon key 'Faceing' in {addon_name}; use 'EndFacing'."
                )
        if 'EndFacing' in myKeys:
            validate_end_facing_values(FigData['EndFacing'])
            tmpList = [
                '' if value == [] else
                (value[0], value[1]) if isinstance(value, (list, tuple)) else value
                for value in FigData['EndFacing']
            ]
            self._EndFacingPos = tmpList
        else:
            self._EndFacingPos = []
        if 'Partner' in myKeys:
            tmpList = []
            for i in range(len(FigData['Partner'])):
                if len(FigData['Partner'][i]) == 2:
                    tmpList.append((FigData['Partner'][i][0], FigData['Partner'][i][1]))
                else:
                    tmpList.append('')
            self.Partner = tmpList
            self._PartnerPos = tmpList

        if not isinstance(Addons, (list, tuple)):
            raise ValueError("Addon selection must be a list of names")
        selected = list(Addons)
        if any(not isinstance(name, str) for name in selected):
            raise ValueError("Addon selection must contain only names")
        if len(set(selected)) != len(selected):
            raise ValueError("An addon cannot be selected more than once")
        self._validate_addon_conflicts(selected, addon_definitions)
        for addon_name in selected:
            if addon_name in addon_definitions:
                addon_data = addon_definitions[addon_name]
            else:
                bars = duration_addon_bars(addon_name)
                if bars is None:
                    if is_malformed_duration_addon(addon_name):
                        raise ValueError(
                            f"Invalid duration addon {addon_name!r}; use B<n> with a positive integer and no leading zero."
                        )
                    raise ValueError(f"Unsupported addon {addon_name!r} for figure {Filename!r}")
                addon_data = {"Name": addon_name, "Bars": bars, "Version": 1}
            self._Addons.append(Figures.FigureAddon(self, addon_data))

        if len(self.StartDancers) != len(self.StartPos):
            raise ValueError(
                f"StartDancers must have the same length as effective StartPos ({len(self.StartPos)}) after addons."
            )
        if len(self.StartFacing) != len(self.StartPos):
            raise ValueError(
                f"StartFacing must have the same length as effective StartPos ({len(self.StartPos)}) after addons."
            )

    @staticmethod
    def _validate_addon_conflicts(selected, definitions):
        from collections.abc import Mapping

        writes = {}
        duration_addons = [name for name in selected if duration_addon_bars(name) is not None]
        if len(duration_addons) > 1:
            raise ValueError(
                f"Conflicting duration addons {duration_addons[0]!r} and {duration_addons[1]!r} both modify Bars."
            )

        fields = ('Bars', 'StartPos', 'EndPos', 'EndFacing', 'Partner')
        if duration_addons:
            for addon_name in selected:
                if addon_name not in duration_addons and isinstance(definitions.get(addon_name), Mapping) and 'Bars' in definitions[addon_name]:
                    raise ValueError(
                        f"Conflicting addons {addon_name!r} and {duration_addons[0]!r} modify Bars."
                    )
        for addon_name in selected:
            data = definitions.get(addon_name, {})
            if not isinstance(data, Mapping):
                raise ValueError(f"Addon definition for {addon_name!r} must be an object")
            for field in fields:
                if field not in data:
                    continue
                values = data[field]
                if field == 'Bars':
                    entries = [(None, values)]
                elif isinstance(values, (list, tuple)):
                    entries = [
                        (index, value)
                        for index, value in enumerate(values)
                        if not is_addon_array_noop(field, value)
                    ]
                else:
                    continue
                for index, value in entries:
                    key = (field, index)
                    if key in writes:
                        previous_name, previous_value = writes[key]
                        dancer = 'all dancers' if index is None else f'dancer {index + 1}'
                        raise ValueError(
                            f"Conflicting addons {previous_name!r} and {addon_name!r} modify "
                            f"{field} for {dancer}: {previous_value!r} vs {value!r}."
                        )
                    writes[key] = (addon_name, value)

            descriptions = data.get('CriptDesc', [])
            replacements = data.get('CriptReplace', [])
            if isinstance(descriptions, (list, tuple)) and isinstance(replacements, (list, tuple)):
                for index, (replacement, target) in enumerate(zip(descriptions, replacements)):
                    if not replacement or not target:
                        continue
                    key = ('CriptDesc', index)
                    value = {'replace': target, 'with': replacement}
                    if key in writes:
                        previous_name, previous_value = writes[key]
                        raise ValueError(
                            f"Conflicting addons {previous_name!r} and {addon_name!r} modify "
                            f"CriptDesc for dancer {index + 1}: {previous_value!r} vs {value!r}."
                        )
                    writes[key] = (addon_name, value)
