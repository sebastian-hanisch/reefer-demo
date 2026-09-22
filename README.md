# Reefer im Block: Wer darf auf die Steckdosen? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-reefer-demo.streamlit.app/)**

Interaktive Fall-Demo zu **Kühlcontainern (Reefern) im Containerblock**: Reefer brauchen Strom und dürfen nur auf Stapel mit Steckdosen. Stellt der Kran dort Normalcontainer ab, fehlt der Platz, wenn
der nächste Reefer kommt: er steht **ohne Strom**. Die Demo beantwortet: **Wie viel Puffer an freien Steckdosen-Plätzen schützt den Strom, ohne den Block zu verstopfen, und ab wann hilft keine Regel
mehr, weil die Steckdosen fehlen?**

Teil des Portfolios für die Website „Sebastian Hanisch – Operations Research und Machine Learning", Zusatz zur Hafen-Linie (Containerblock; setzt auf der Stapelplanung `stapelplanung-demo` auf: gleicher
Block, gleiche Ereignisfolge, gleiche Umstapel-Regel Bestfit).

## Warum dieses Problem

Naheliegend wäre „Steckdosen-Stapel möglichst streng für Reefer reservieren“. Gemessen ist das **teuer, sobald die Steckdosen reichlich sind**, und Nichtstun lässt Reefer ohne Strom stehen. Dazwischen liegt eine
Regel mit **einem** Regler, dem **Steckdosen-Puffer** B: ein Normalcontainer darf auf einen Steckdosen-Stapel, solange danach noch B Steckdosen-Plätze frei bleiben. B = 0 ist „Steckdosen egal“, B gleich allen
Steckdosen-Plätzen ist „reserviert“; die drei Regeln sind eine Familie. Zwei Fragen sind getrennt: **wie viele Steckdosen-Stapel** der Block hat (das legt die Untergrenze fest) und **wer auf ihnen stehen darf**
(der Puffer).

## Modell

Block wie in der Stapelplanung: *n* Stapel der Höhe *H*, Ereignisfolge aus Ankünften und Abholungen (Belegungsgrenze Füllgrad × (*n* − 1) × *H*), verrauschte Abfahrtsschätzung mit Fehler σ (Bruchteil der
mittleren Standzeit); die Erzeugung ist **bitgleich** zur Stapelplanung-Demo (Test gegen feste Referenzwerte). Neu: die ersten *s* Stapel haben in jeder Lage eine Steckdose (*K* = *s*·*H* Steckdosen-Plätze); jeder
Container ist mit Wahrscheinlichkeit *q* ein Reefer. Ein Reefer kommt per Bestfit auf einen Steckdosen-Stapel mit Platz, sonst steht er **ohne Strom** in einem anderen Stapel und bleibt dort bis zur Abholung
(Annahme). Eine Ankunft ohne Strom ist **durch Normalcontainer blockiert**, wenn zu diesem Zeitpunkt ein Normalcontainer auf einem Steckdosen-Platz stand, sonst ist die **Kapazität erschöpft** (Momentaufnahme,
kein Gegenfaktisches). Formal im Expander „📐 Mathematische Formulierung“.

## Methodik – drei Regeln, ein Regler

Alle Regeln arbeiten denselben Block ab; Referenz aller Vergleiche ist **Steckdosen egal** (Bestfit ohne Rücksicht auf die Steckdosen, nicht die Alltagsregel „Niedrigster Stapel“: deren Abstand zu Bestfit ist die
Geschichte der Stapelplanung, nicht die der Reefer).

- **Steckdosen egal** (B = 0): Normalcontainer per Bestfit über alle Stapel mit Platz.
- **Steckdosen-Puffer** (B): auf einen Steckdosen-Stapel nur, wenn danach mindestens B Plätze mit Steckdose frei bleiben. **Faustregel** B ≈ Reefer-Anteil × Belegungsgrenze (erwartete Zahl Reefer im Block).
- **Steckdosen reserviert** (B = alle Steckdosen-Plätze): Normalcontainer nur auf Stapel ohne Steckdose (nur wenn dort nichts frei ist, auch auf Steckdosen-Stapel).

Die **Stichprobe** (50 Blöcke mit den Seeds 0 bis 49, nicht der eingestellte Seed) und die **Kurven** (Puffer-Kurve und Steckdosen-Kurve, je 30 Blöcke) rechnen in wenigen Sekunden und brauchen keinen Knopf
(der größte Block rund 8 s; alles ist im Cache, solange sich die Einstellungen nicht ändern).

## Befunde (gemessen, keine Behauptungen)

8 Stapel, 5 Lagen, Füllgrad 80 %, 300 Container, Schätzfehler 50 %; Zahlen aus `tools/PRESET_SWEEP.md` und der Vorab-Messreihe (`hafen-planung/messreihe_reefer/ERGEBNIS.md`, `sweep4.json`).

| Frage | Befund |
|---|---|
| **Sind die drei Regeln wirklich eine Familie?** | Ja: Puffer 0 = „egal“, Puffer ≥ Steckdosen-Plätze = „reserviert“, bitgleich, in 180 Läufen der Messreihe (`check.py`) und 40 Zufallsszenarien der Tests (`test_the_family_limits_are_exactly_the_two_special_rules`). |
| **Wie viele Reefer stehen ohne Strom?** | 20 % Reefer, 3 Steckdosen-Stapel (15 Plätze): egal **1,06** je Block, Puffer (B = 6) **0,01**, reserviert 0. Alle 1,06 sind durch Normalcontainer blockiert. |
| **Was kostet das an Umstapelungen?** | Je Abholung egal 0,778, Puffer 0,798 (**+2,6 %**), reserviert 0,933 (**+19,9 %**). Der Aufschlag des Puffers ist klein, aber klar von null verschieden; ein Vorteil bei den Umstapelungen ist **nicht** belegt. |
| **Ist Reservieren immer schlecht?** | Nein, nur wenn die Steckdosen reichlich sind: 10 % Reefer, 4 Steckdosen-Stapel: **+51,5 %**; ohne Reefer +66 %. Bei knappen Steckdosen kostet es nichts (2 Stapel: −1,6 %). |
| **Wo liegt das Knie?** | Puffer-Kurve (3 Steckdosen-Stapel): der Strom ist ab B ≈ 5 gesichert (0,01), die Umstapelungen steigen erst danach spürbar (B = 8: 0,839, B = 10: 0,883, B = 15: 0,933). |
| **Stimmt die Faustregel?** | An zwölf Einstellungen (Reefer-Anteil 10 bis 40 %, 3 bis 5 Steckdosen-Stapel) höchstens 0,07 blockierte Ankünfte je Block; der Aufschlag an Umstapelungen gegen „egal“ liegt zwischen −5 % und +6 %, in zehn von zwölf Fällen höchstens +2 %. Empirisch, nicht bewiesen. |
| **Was tun bei zu wenigen Steckdosen?** | 30 % Reefer, 2 Stapel: selbst „reserviert“ lässt 1,83 Reefer ohne Strom (Kapazität erschöpft); egal 9,54. Den Rest löst nur ein weiterer Steckdosen-Stapel. |
| **Presets** | Eine gemeinsame Block-Nummer (Seed 490) für alle fünf; jede Kennzahl zwischen dem 10. und 90. Perzentil der Grundgesamtheit. Von 500 Seeds tragen 56 alle fünf Geschichten. |

## Ehrliche Grenzen

- Ein Reefer ohne Strom **bleibt** es bis zur Abholung (in der Praxis wird er umgesteckt); gezählt wird nur das Ereignis, nicht die Dauer. **Keine** Anschlussleistung, Temperaturklassen oder Überwachungszeiten.
- Der Reefer-Anteil ist unabhängig je Container gezogen (keine Ladungslisten, keine Gruppen nach Schiff oder Kunde).
- **Reefer-Racks** (einreihige Gestelle ohne Blockieren) sind ein anderes Lagerkonzept und nicht modelliert.
- Die **Lage der Steckdosen-Stapel** (links) und die **Reihenfolge bei Gleichstand** in Bestfit sind Modellwahlen; sie verschieben alle Umstapelzahlen um 2 bis 4 %, nicht die Rangfolge der Regeln (gemessen, Steckdosen-Stapel
  links gegen rechts).
- Die **Faustregel** ist empirisch geprüft, nicht bewiesen; die Puffer-Kurve zeigt für jede Einstellung, wo das Knie wirklich liegt.
- Alle Zahlen sind **Größenordnungen aus einer Simulation, keine Messung an echten Terminals.**

## Design-Entscheidungen und Funde

**Ein scheinbarer Vorteil war ein Artefakt.** Ein erster Messlauf zeigte den Puffer *besser* als „egal“ bei den Umstapelungen (−1 bis −3 %, mehrere Standardfehler). Ursache war die Reihenfolge, in der Bestfit die
Kandidaten bei Gleichstand bekam (Steckdosen-freie Stapel zuerst). Mit einer einzigen kanonischen Reihenfolge (Stapelindex) und dem Nachweis, dass die Grenzfälle B = 0 und B = alle die Sonderregeln **bitgleich**
treffen, verschwand er. Deshalb steht die Familien-Gleichheit als eigener Test da, und die Regeln geben Bestfit die Kandidaten nie in einer regelabhängigen Reihenfolge.

**Blockiert oder Kapazität statt vermeidbar und unvermeidbar.** Die Trennung ist eine Momentaufnahme („stand ein Normalcontainer auf einem Steckdosen-Platz?“), keine Aussage darüber, was eine andere Regel erreicht
hätte; die Begriffe sagen das.

**Referenz ist „egal“, nicht die Alltagsregel.** Sonst würde ein Teil des Abstands (Bestfit gegen Ausgleich der Höhen) fälschlich den Steckdosen zugeschrieben.

**Alles ganzzahlig, alles deterministisch.** Kein Löser, keine Zeitgrenze: die Preset-Kriterien und Tests hängen nicht vom Rechner ab. Am gezeigten Block gelten die Kriterien in ganzen Zahlen, im Mittel über
200 Blöcke in Bruchteilen; jedes Kriterium hat einen Test mit künstlichen Werten, der einzeln an seiner Schwelle kippt.

**Berechnete Grenzen werden begrenzt, nicht verworfen.** Steckdosen-Stapel (höchstens Stapel − 1) und Puffer (höchstens alle Steckdosen-Plätze) hängen von anderen Reglern ab; Permalink, Preset und geänderte Stapelzahl
begrenzen sie vor dem Erzeugen der Regler (`clamp_settings`), und ohne Steckdosen-Stapel entfällt der Puffer-Regler samt Hinweis.

## Tests

`python -m pytest tests/ -v` – 204 Tests, rund 3,5 Minuten. Zusammensetzung:

- **Szenario:** Ereignisfolge und Schätzung bitgleich zur Stapelplanung, Reefer-Zuordnung (Extremwerte, Determinismus, ein größerer Anteil enthält den kleineren), Faustregel, Fehlerfälle.
- **Regeln und Ablauf:** Bestfit-Fälle einzeln, Puffer-Semantik, Kandidatenreihenfolge; die Zähler gegen eine **unabhängige, bewusst einfache Nachrechnung** auf 60 Zufallsszenarien, Familien-Gleichheit, Invarianten je
  aufgezeichnetem Schritt, Randfälle (0 Reefer, 0 Steckdosen-Stapel, nur Reefer, kleinster Block), Reproduktion der Messreihe.
- **Auswertung:** Stichprobe, Kurven gegen Direktrechnungen, Urteil in drei Zuständen und genau an der Schwelle, Verteilung, Diagnose.
- **Figuren:** Blockansicht (Farben, Ränder mit Vorrang, Hover), Kurven, Verteilung, Vergleich; alle Achsen fest.
- **Presets:** Geschichte am gezeigten Block, im Mittel von 200 Blöcken, typisch je Kennzahl; alle Kriterien einzeln an ihren Schwellen mit künstlichen Werten.
- **PDF:** Inhalt Zelle für Zelle, genaue Sonderzeichen (fpdf2 stürzt bei „–“, „€“ und Emoji ab), Randfälle.
- **End-to-End (AppTest):** Skelett und Footer, jedes Preset, Permalink mit berechneten Grenzen, alle Regler an Min und Max, die bedingte Meldung in allen Zuständen, Urteil in allen Zuständen, Blick in den Block,
  Vergleichstabelle, PDF, Texte.

Zusätzlich wurde jedes Modul mit **eingebauten Fehlern** geprüft (`tools/mutation_check.py`, 103 Mutanten). Der erste Lauf fand 97; von den sechs Überlebenden waren zwei echte Lücken (Vorzeichen der Prozentangabe im PDF, ein Test der Klarheitsschwelle, der die Schwelle aus dem Code las) und sind geschlossen und erneut geprüft, einer (Ergebnis ohne Abholungen) ist durch einen Test abgedeckt, aber nicht erneut gemutet. Drei sind **gleichwertig**: die Klarheitsschwelle genau bei zwei Standardfehlern (Gleitkommagrenze), das Kurvenraster bei genau zwölf Punkten (fällt mit allen Werten zusammen) und der Vergleich der Umstapelungen als ganze Zahlen statt als Bruch (gleiche Abholungen, gleiche Division). Ein Mutant (Blocker landet wieder im Quellstapel) läuft in eine Endlosschleife; das Werkzeug zählt das seit dem ersten Lauf als gefunden.

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Hauptablauf: Presets, Sidebar, Hauptansicht, Blick in den Block, Kernabschnitt, Regelvergleich, Texte |
| `rfr_constants.py` | Regler-Grenzen, `PRESETS`, Regeln, Farben, feste Parameter |
| `rfr_presets.py` | `SETTING_SPECS`, Permalink (Begrenzen und Einrasten), berechnete Grenzen, Presets, Seed-Knopf |
| `rfr_scenario.py` | Ereignisfolge, Abfahrtsschätzung (wie Stapelplanung), Reefer-Zuordnung, Faustregel |
| `rfr_rules.py` | Bestfit und die Einlagerungsregel mit Steckdosen-Puffer |
| `rfr_simulation.py` | Ablauf, Umstapeln, Zähler (ohne Strom, blockiert, Kapazität), aufgezeichnete Schritte |
| `rfr_evaluation.py` | Regeln auf einem Block, Stichprobe, Puffer-Kurve, Steckdosen-Kurve, gepaarte Differenz, Verteilung, Urteil, Diagnose |
| `rfr_visualization.py` | Blockansicht, Kurven, Verteilung, Vergleich (alle Achsen fest) |
| `rfr_ui_panel.py` | Panel je Regel (Kennzahlen 2 × 2, kumulierte Umstapelkurve) |
| `rfr_pdf_export.py` | PDF-Ergebnis (`fpdf2`, Kernschrift, Sonderzeichen-Bereinigung) |
| `rfr_stories.py` | Abnahmekriterien der Presets (Quelle für Werkzeug und Tests) |
| `tools/tune_presets.py`, `tools/PRESET_SWEEP.md` | Preset-Abstimmung und ihr Bericht |
| `tools/mutation_check.py` | Fehler-Einbau-Test |
| `tests/` | siehe oben |

## Bewusst nicht umgesetzt (mögliche Erweiterungen)

- **Reefer-Racks** (einreihige Gestelle ohne Blockieren) als eigenes Lagerkonzept.
- **Anschlussleistung und Temperaturklassen**, **Umstecken nach Freiwerden einer Steckdose** (Dauer ohne Strom statt Ereignis), **Reefer-Gruppen** nach Schiff oder Kunde.
- **Steckdosen nur in den unteren Lagen** und ein **Abfahrtsprozess mit Gruppen**.
- **Exakte Referenz auf kleinen Blöcken** (IDA*-Suche mit Steckdosen-Nebenbedingung): die Frage ist eine Regel-Frage, keine Optimalitätsfrage.

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `python -m pytest tests/ -v`. Preset-Abstimmung: `python tools/tune_presets.py population|seeds`. Fehler-Einbau: `python tools/mutation_check.py`.

---
