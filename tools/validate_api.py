from GUI_DanceCreator_App import app, load_Figuers

if __name__ == '__main__':
    # Lade Figuren aus Figures/ (falls vorhanden)
    load_Figuers()
    client = app.test_client()
    resp = client.get('/figures')
    print('STATUS:', resp.status_code)
    try:
        data = resp.get_json()
        print('NUM FIGURES:', len(data))
        # print first item for inspection
        if data:
            import json
            print('FIRST:', json.dumps(data[0], indent=2, ensure_ascii=False))
    except Exception as e:
        print('Fehler beim Auswerten der Antwort:', e)

