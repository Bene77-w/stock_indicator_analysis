# Entscheidungen — feature/gui-flask

## Implementierungsentscheidungen

| Entscheidung/Annahme | Begründung | Bezug (Spec/Ticket/Datei) |
|---|---|---|
| Keine Spec/Tickets vorhanden; Commit-Messages (`7bd19b0..f1dcf3a`) und README gelten als Sollvorgabe | Vorgabe des Users vor dem Final Review | — |
| `main` vor dem Review in den Branch gemergt (`83cee18`) | Review soll exakt den Stand prüfen, der nach `main` geht (User-Vorgabe) | Merge-Commit |
| Konflikt `stock_analyser.py`: Branch-Version übernommen | `main` hatte nur die unveränderte Datei umbenannt (`stock_analyzer.py` → `stock_analyser.py`), der Branch enthält das Refactoring | `stock_analyser.py` |
| README: englische Fassung aus `main` als Basis, Inhalte des Branches (CLI-Optionen, GUI, Projektstruktur, Tests, Rechenwege) ins Englische übertragen, Lizenzabschnitt behalten | `main` hat die README fürs öffentliche Repo auf Englisch umgestellt; die Doku des Branches beschreibt den aktuellen Funktionsumfang | `README.md` |

## Reviewbefunde

| Befund und Auswirkung | Schweregrad laut Prüfer | Prüfer, Review, Runde | Bezug (Spec/Ticket/`datei:zeile`) | Umgang | Begründung/Belege |
|---|---|---|---|---|---|
