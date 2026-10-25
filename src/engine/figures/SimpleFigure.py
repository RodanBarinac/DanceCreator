import os
import json
import math
import re
from ..models import Figures
from ..models import DanceFloor as DF
from .addon_utils import duration_addon_bars, is_malformed_duration_addon

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
            facing = self.EndFacing[i] if len(self.EndFacing) > i else None
            tmpFacing = (
                self.posWithAnchor(facing)
                if isinstance(facing, (list, tuple)) and len(facing) == 2
                else []
            )
            newDF.addDancer(oldDF.DancerbyPos(tmpStartPos), tmpEndPos, tmpFacing)

        return newDF

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
                base_facing = self._EndFacingPos[i] if len(self._EndFacingPos) > i else ''
                facing = (
                    base_facing
                    if isinstance(base_facing, (list, tuple)) and len(base_facing) == 2
                    else (self.EndFacing[i] if len(self.EndFacing) > i else '')
                )
                if isinstance(facing, (list, tuple)) and len(facing) == 2:
                    myCript = myCript.replace(
                        '{Face}', myDF.PosNamebyPos(self.posWithAnchor(facing))
                    )
                else:
                    raise Exception("Sorry, noone to face!")

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
            if isinstance(addon_data, dict) and 'Faceing' in addon_data:
                raise ValueError(
                    f"Unsupported legacy addon key 'Faceing' in {addon_name}; use 'EndFacing'."
                )
        if 'EndFacing' in myKeys:
            tmpList = []
            for i in range(len(FigData['EndFacing'])):
                if len(FigData['EndFacing'][i]) == 2:
                    tmpList.append((FigData['EndFacing'][i][0], FigData['EndFacing'][i][1]))
                else:
                    tmpList.append('')
            self._EndFacingPos = tmpList
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
                    entries = [(index, value) for index, value in enumerate(values) if value not in (None, [], '')]
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
