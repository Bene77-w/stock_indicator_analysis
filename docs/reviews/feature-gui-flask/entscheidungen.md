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
| Tautologische Erwartungswerte bei MACD- und Bollinger-Tests (gleiche pandas-Ausdrücke wie im Code) | MITTEL | Generalist, Final Review, Runde 1 | `tests/test_indicators.py` (MACD/Bollinger-Abschnitt) | akzeptiertes Risiko | Die Formeln sind direkte pandas-Standardaufrufe ohne eigenes Seeding; die Verhaltenstests (Kreuzungen, Crash/Spike, Warm-up) prüfen die Signallogik unabhängig. Für RSI, das eigenes Seeding hat, gibt es jetzt einen Referenztest |
| Indikator-Dispatch und Standardwerte stehen in CLI (`calculate`, argparse) und GUI (`build_frames`, `PARAMETER_DEFAULTS`) doppelt | NIEDRIG | Generalist, Final Review, Runde 1 | `stock_analyser.py:99-122`, `stock_analyser_gui.py:98-111` | akzeptiertes Risiko | Drei feste Indikatoren, kein neuer geplant; gemeinsamer Dispatch wäre ein eigener Umbau ohne aktuellen Nutzen |
| Tabelle „Most recent values“ zeigt bei `all` nur RSI | NIEDRIG | Generalist, Final Review, Runde 1 | `stock_analyser_gui.py:263-264` | sachlich widerlegt | Bewusstes Verhalten aus Commit 285c12e („table heading names the indicator shown“); die Überschrift nennt den gezeigten Indikator, alle drei stehen in Charts und Signalliste |
| Feld `hidden` im Signal-Payload bedeutet „leer“ | NIEDRIG | Generalist, Final Review, Runde 1 | `stock_analyser_gui.py:205`, `templates/index.html:162` | akzeptiertes Risiko | Reine Benennung, intern, korrekt verwendet |
| Ungültige CLI-Parameter wiederholen im interaktiven Menü jede Runde denselben Fehler | NIEDRIG | Generalist, Final Review, Runde 1 | `stock_analyser.py` `_interactive` | akzeptiertes Risiko | Die Meldung nennt den Parameter; das Menü fragt Parameter bewusst nicht ab, Korrektur durch Neustart mit richtiger Option |
| Periodenwert in der CLI case-sensitiv (`1Y` abgelehnt) | NIEDRIG | Generalist, Final Review, Runde 1 | `market_data.py` `VALID_PERIODS` | sachlich widerlegt | Laut Prüfer selbst kein Fehler: konsistent mit yfinance, klare Fehlermeldung mit gültigen Werten |
