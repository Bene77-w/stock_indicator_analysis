# Stock Analyzer

Kleines Python-Kommandozeilenprogramm zur Analyse von Aktienkursen über Yahoo Finance.
Es zeigt Unternehmens- und Kursdaten und berechnet wahlweise RSI, MACD oder Bollinger Bänder –
einzeln oder alle zusammen mit kombinierter Signaltabelle.

## Installation

Im Projektordner eine virtuelle Umgebung anlegen und die Abhängigkeiten installieren:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Start

### Interaktiv

```bash
python3 stock_analyser.py
```

Das Programm fragt Tickersymbol (zum Beispiel `AAPL`), Zeitraum (zum Beispiel `1y` oder `3mo`)
und Indikator ab. Mit `q` an jeder Eingabeaufforderung beenden Sie das Programm.
Ungültige Eingaben (falsches Symbol, unbekannter Zeitraum oder Indikator) werden abgefangen,
die Abfrage startet erneut.

### Als Kommandozeilenbefehl

```bash
python3 stock_analyser.py AAPL 1y rsi                     # RSI (14 Tage) über 1 Jahr
python3 stock_analyser.py AAPL 6mo macd --signals-only    # nur Zeilen mit Kauf/Verkauf-Signal
python3 stock_analyser.py AAPL 1y bollinger --bb-std 2.5  # Bollinger Bänder mit 2,5 Standardabweichungen
python3 stock_analyser.py AAPL 1y all --tail 30           # alle Indikatoren kombiniert
python3 stock_analyser.py --help                          # alle Optionen
```

Parameter können überschrieben werden, zum Beispiel `--rsi-period 21`, `--macd-fast 12 --macd-slow 26 --macd-signal 9`,
`--bb-period 20 --bb-std 2.0`, `--rsi-oversold 30 --rsi-overbought 70`.

### Grafische Oberfläche (Browser)

```bash
python3 stock_analyser_gui.py
```

Danach im Browser http://127.0.0.1:5000 öffnen. Die Oberfläche bietet dasselbe Formular wie die
Kommandozeile, dazu Kurs-Charts (mit Bollinger-Bändern, RSI mit Kauf/Verkauf-Grenzen und MACD),
die letzten Kurswerte und eine Signalliste mit Datum. Genauso wie im Terminalmodus werden
ungültige Eingaben abgefangen und als Meldung angezeigt statt abstürzen zu können.
Die Seite läuft nur lokal auf `127.0.0.1`; Chart.js wird per CDN geladen, die Kursdaten kommen
weiterhin von Yahoo Finance.

Zwei Besonderheiten gegenüber dem Terminalmodus:

- Gleichem Ticker/Zeitraum wird nur einmal pro 5 Minuten nachgeladen – das Umschalten
  zwischen den Indikatoren ist dadurch sofort, nutzt aber Daten von maximal 5 Minuten Alter.
- Charts zeigen die letzten 252 Handelstage, die Signalliste die letzten 100 Signale
  (mit Hinweis, wenn gekürzt wurde). `GET /health` liefert `{"status": "ok"}`, falls man
  prüfen will, ob der Server läuft.

## Projektstruktur

| Datei                   | Aufgabe                                                       |
| ----------------------- | --------------------------------------------------------------- |
| `stock_analyser.py`     | Kommandozeilen-Oberfläche: Eingabe, Ausgabe, Ablaufsteuerung   |
| `stock_analyser_gui.py` | Grafische Oberfläche im Browser (Flask + Chart.js)             |
| `market_data.py`        | Datenabruf bei Yahoo Finance (einzige Stelle mit Netzwerkzugriff) |
| `indicators.py`         | Reine Berechnung von RSI, MACD und Bollinger Bändern           |
| `templates/index.html`  | Seitenvorlage der grafischen Oberfläche                        |
| `tests/`                | pytest-Tests für alle Module, ganz ohne Netzwerk               |

## Tests

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

Die Tests laufen offline: Der Netzwerkzugriff wird in `tests/test_market_data.py`,
`tests/test_cli.py` und `tests/test_gui.py` durch Stubs ersetzt, die Indikator-Tests rechnen
mit festen Kursreihen.

## Rechenwege

- **RSI** nach Wilder: Gewinn-/Verlustmittel über exponentielle Glättung mit `alpha = 1/Periode`
  (entspricht TA-Lib und gängigen Chartprogrammen), Kauf unter `--rsi-oversold`, Verkauf über `--rsi-overbought`.
- **MACD** = EMA(kurz) − EMA(lang), Signallinie = EMA über dem MACD; kauft bei Überquerung der Signallinie von unten,
  verkauft bei Unterquerung. Die Aufwärmphase der EMAs wird ignoriert.
- **Bollinger Bänder** um einen gleitenden Durchschnitt; Kauf unter dem unteren Band, Verkauf über dem oberen Band.
  Liegen beide Bänder auf dem Preis (keine Volatilität), gewinnt das Verkaufssignal.

Alle Ausgaben sind technische Kennzahlen und keine Anlageberatung.
