# Forschungszulage-Assistent

Eine Python-3.11-Entwurfshilfe für deutsche Projektbeschreibungen zu Software-FuE. Sie liest YAML oder JSON, gibt erklärbare Hinweise zu fünf FuE-Merkmalen, trennt deklarierte Routinearbeit von Forschungsarbeit, erstellt eine Kostenplanung und erzeugt deutsche Entwürfe als Markdown und PDF.

**Keine Rechts- oder Steuerberatung. Keine Förderentscheidung. Kein amtlicher Antrag und keine Einreichung bei BSFZ oder Finanzamt.** Die Anwendung übernimmt Angaben des Antragstellers und ersetzt keine fachliche oder steuerliche Prüfung.

Alles wird auf GitHub Actions gebaut, getestet und mit drei synthetischen Beispielen ausgeführt. Es werden keine weiteren Konten, API-Schlüssel, externen Dienste, lokalen Installationen oder lokalen Docker-Container benötigt. Markdown, PDF, gerenderte PDF-Seiten und Messberichte stehen im Artefakt `generated-drafts-and-reports` einer abgeschlossenen [CI-Ausführung](https://github.com/hamza2829/forschungszulage-assistent/actions).

## Drei Befehle

Diese Befehle laufen in CI. In einer bereits eingerichteten Python-Umgebung mit installiertem Paket funktionieren sie auch optional lokal. Für dieses Projekt sind keine manuellen lokalen Schritte erforderlich.

Kriterien prüfen:

```sh
python -m forschungszulage check examples/logistikplaner.yaml
```

Prüfung, Rechnung, Markdown und PDF erzeugen:

```sh
python -m forschungszulage analyze examples/logistikplaner.yaml --output generated/logistikplaner
```

API starten:

```sh
python -m forschungszulage serve --port 8000
```

Die API bietet `POST /api/projects` für ein JSON-Projekt und `POST /api/projects/yaml` für YAML mit `Content-Type: application/yaml`. Antworten enthalten `check`, `calculation`, `draft_markdown` und `pdf_base64`. Die interaktive Schema-Dokumentation liegt unter `/docs`. Ein FastAPI-TestClient prüft die API in CI, ohne einen öffentlichen Server oder externen Dienst zu benötigen. Die CLI bietet zusätzlich `calculate` für die Kostentabelle und `draft` für die Dokumentausgabe. Mit `--config DATEI.yaml` lässt sich die Konfiguration bei Berechnung und Dokumenterzeugung ersetzen.

## Aufbau und Eingabe

`models.py` prüft die Struktur mit Pydantic. `criteria.py` enthält eine eigene Klasse je Kriterium und die Routineabgrenzung. `calculation.py` rechnet mit `Decimal`. `documents.py` nutzt Jinja2 für Markdown und ReportLab für PDF. API und CLI verwenden denselben Service. Der Dienst speichert keine Projekte und führt keine Netzwerkabfragen aus.

Die Beispiele enthalten deutsche Texte und ausschließlich synthetische Namen:

| Datei | Zweck |
| --- | --- |
| `examples/logistikplaner.yaml` | Hypothesen und Vergleichsversuche eines adaptiven Tourenplaners, zwei Personen, ein getrenntes Routinepaket |
| `examples/ki-klassifikation.yaml` | Experimentelle Kalibrierung bei synthetischem Datendrift, FuE-Anteile und Abzug bereits geförderter Kosten |
| `examples/datenplattform.json` | Bewusstes Routinebeispiel mit Standardkonnektoren, fehlender technischer Ungewissheit und offenen Punkten |

Pflichtfelder sind Titel, Beginn und Ende. Fehlende fachliche Texte erzeugen offene Punkte. Personalkosten benötigen je Person entweder `hourly_rate` oder `monthly_salary` zusammen mit `monthly_hours`. Das Gehalt und der Stundensatz müssen auf tatsächlich geeigneten Arbeitnehmer-Entgeltkosten beruhen. Ein externer Verkaufssatz ist keine geeignete Eingabe. Förderfähige Arbeitgeberbeiträge können als tatsächlicher Betrag je Stunde über `hourly_employer_contribution` ergänzt werden; es gibt keinen pauschal erfundenen Arbeitgeberaufschlag.

Jedes Arbeitspaket hat Termine und Zuordnungen mit `person_id`, `person_days`, `research_fraction` und optional `already_funded_costs`. Der FuE-Anteil ist eine Annahme des Antragstellers. Mit `activity: routine` wird das Paket in der Kostenbasis mit null berücksichtigt. Negative, nicht endliche oder widersprüchliche Werte, unbekannte Personen und doppelte IDs werden abgelehnt. Arbeitspakete über eine Jahresgrenze müssen in getrennte Pakete aufgeteilt werden. Die mitgelieferte Konfiguration akzeptiert nur Aufwendungen im Jahr 2026; andere Zeiträume benötigen eine überprüfte Konfiguration.

## Kriterien und Routineabgrenzung

Die fünf Merkmale sind Neuartigkeit, Kreativität, Ungewissheit, Systematik und Reproduzierbarkeit. Jeder Befund enthält `ok`, `weak` oder `missing`, eine deutsche Begründung, eine Frage und die geprüften Eingabefelder. `ok` bedeutet nur, dass die beschriebenen Textmerkmale vorhanden sind.

Die [BSFZ](https://www.bescheinigung-forschungszulage.de/hilfen-zur-antragstellung) arbeitet mit drei übergeordneten Prüfkriterien: Neuartigkeit, Risiko / Unwägbarkeit und Planmäßigkeit. Die fünf Merkmale dieses Werkzeugs sind eine ergänzende Entwurfscheckliste und werden nicht als fünf eigenständige amtliche BSFZ-Prüfungen ausgegeben.

Die Regeln prüfen Textvorhandensein, Mindestumfang und benannte Merkmale. Für technische Ungewissheit werden technische Begriffe und Unsicherheitsbegriffe gemeinsam gesucht. Ausschließlich angegebene Standardmethoden, fehlende technische Ungewissheit und fehlende Messplanung führen zu Rückfragen. Reine Budget- und Marktrisiken erfüllen diese technische Textregel nicht. Gute Formulierungen können sachlich falsch sein; die Software erkennt das nicht.

## Quellen, Rechtsstand und Berechnung

**Sätze und Grenzen müssen vor jeder Nutzung erneut anhand der amtlichen Quellen geprüft werden.** Die Anwendung aktualisiert sie nicht automatisch. In [`src/forschungszulage/data/rates.yaml`](src/forschungszulage/data/rates.yaml) hat jeder Wert eine Quelle, ein `stand`-Datum, eine Einheit und eine Erläuterung. Prüfung dieser Quellen: 04.11.2026.

| Wert | Konfiguration | Grundlage |
| --- | ---: | --- |
| Regulärer Fördersatz | 25% | [BMF-Schreiben vom 27.10.2026, Rn. 188](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Weitere_Steuerthemen/Forschungszulagen/2026-10-27-gewaehrung-von-forschungszulage.pdf?__blob=publicationFile&v=7) |
| Erhöhter Satz bei angenommenem KMU-Status und beantragter Erhöhung | 35% | [BSFZ-Überblick](https://www.bescheinigung-forschungszulage.de/neu-hier) |
| Jährliche Höchstbemessungsgrundlage ab 2026 | 12.000.000 EUR | [BSFZ zu den Änderungen](https://www.bescheinigung-forschungszulage.de/steuerliches-investitionssofortprogramm), BMF Rn. 166b und 174 |
| Gemeinkosten bei Vorhabenbeginn ab 01.01.2026 | 20% | BMF Rn. 154a bis 154c, [§ 3 Abs. 3b FZulG](https://www.gesetze-im-internet.de/fzulg/__3.html) |
| Beihilfegrenze je Unternehmen und FuE-Vorhaben | 15.000.000 EUR | [§ 4 Abs. 3 FZulG](https://www.gesetze-im-internet.de/fzulg/__4.html) |
| Umrechnung geplanter Personentage | 8 Stunden pro Tag | Frei konfigurierbare Planungsannahme, kein gesetzlicher Tagessatz; tatsächliche Stundenaufzeichnung bleibt erforderlich |

Die BMF-Datei wurde direkt vom amtlichen Server geladen und für diese Werte gelesen. Die im Werkzeug verwendeten Arbeitnehmerkosten folgen dem Ansatz tatsächlicher Entgeltkosten. Die seit 2026 geltende Eigenleistungsregel für Einzelunternehmer mit 100 EUR je Stunde und höchstens 40 Wochenstunden wird hier bewusst nicht auf Arbeitnehmer angewendet. Eigenleistungen werden nicht berechnet.

Rechenweg je Zuordnung: Personentage mal konfigurierte Tagesstunden mal Entgeltkosten je Stunde; davon deklarierter FuE-Anteil, anschließend Abzug bereits anderweitig geförderter Kosten. Bei Monatsgehalt lautet der Plan-Stundensatz Monatsgehalt geteilt durch die angegebenen vertraglichen Monatsstunden. Geeignete Arbeitgeberbeiträge werden als eingegebener Stundenbetrag ergänzt. Geldbeträge werden mit `Decimal` auf Cent kaufmännisch gerundet. Es folgen gegebenenfalls Gemeinkosten, die verfügbare Jahresbasis und der ausgewählte Fördersatz. Die Beihilfegrenze begrenzt anschließend die geschätzte Zulage.

`other_annual_base` muss die bereits beanspruchte Bemessungsgrundlage anderer Vorhaben und verbundener Unternehmen je Jahr enthalten. `other_project_aid` vermindert den noch verfügbaren Beihilferahmen. Ohne diese Angaben wird jeweils null angenommen und ausdrücklich darauf hingewiesen. Bei knapper Jahresbasis werden Arbeitspakete in Eingabereihenfolge berücksichtigt. Das ist eine transparente Planungszuordnung, keine gesetzlich vorgeschriebene Verteilung.

## Beispielausgabe

Die tatsächlichen Beispielwerte werden nach der ersten erfolgreichen CI-Ausführung hier eingetragen.

## Gemessene CI-Ergebnisse

<!-- CI_METRICS_START -->
| Messwert | GitHub Actions |
| --- | --- |
| Tests und Abdeckung | Erste abgeschlossene Messung steht aus |
<!-- CI_METRICS_END -->

CI installiert das Paket ausschließlich auf dem GitHub-Runner, führt pytest mit mindestens 80% Gesamtabdeckung aus und prüft zusätzlich mindestens 80% Zeilenabdeckung aus `coverage.xml`. Es gibt keine Abdeckungsausschlüsse. `ci/measure.py` liest echte XML-Zähler und schreibt die Tabelle und JSON-Werte in das Artefakt und die Actions-Zusammenfassung. Die aufgelösten Paketversionen werden ebenfalls aufgezeichnet.

Anschließend laufen die CLI und beide Eingabeformate auf allen drei Beispielen. CI erzeugt Markdown und PDF, prüft ihren Text und rendert jede PDF-Seite als PNG zur visuellen Kontrolle. Die Tests prüfen jede Kriteriumsregel, die Routineabgrenzung, Gehalt und Stundensatz, null Tage, Grenzen, Konfigurationsfehler, ungültige Eingaben, Dokumente und die API einschließlich aller Beispiele.

## Grenzen

Dies ist ein regelbasierter Entwurfshelfer. Er bestätigt keine Forschungsleistung, Förderfähigkeit, Antragstauglichkeit, steuerliche Anspruchsberechtigung oder Bewilligung. Er reicht nichts ein und verlangt dafür keine Konten. Die Projektbeschreibung folgt den genannten Entwurfsabschnitten; sie bildet kein amtliches Formular samt Zeichenlimits vollständig nach.

Die Kostenplanung umfasst nur Arbeitnehmer-Personalkosten und die darauf bezogene Gemeinkostenpauschale. Eigenleistungen, Mitunternehmervergütungen, Auftragsforschung, Abschreibungen, vollständige Beihilfe- und De-minimis-Prüfungen, abweichende Wirtschaftsjahre, KMU-Einstufung und arbeitsrechtliche oder steuerliche Einzelfragen sind nicht implementiert. Mehrere Projekte und verbundene Unternehmen werden nur über die angegebenen Vorbelastungen berücksichtigt. Tatsächliche Stunden, Personalkapazitäten, Überschneidungen, Feiertage und die Geeignetheit der eingegebenen Entgeltbestandteile werden nicht geprüft.

Die Beispiele sind synthetisch und keine anerkannten Anträge. Texte werden aus den Eingaben zusammengesetzt; es gibt kein Sprachmodell und keine Recherche zur behaupteten Neuartigkeit. Die PDF-Schrift deckt die für die deutschen Beispiele verwendeten Zeichen ab. Der lokale Entwicklungsserver lauscht nur auf der Loopback-Schnittstelle. Die API hat keine Authentifizierung und ist nicht als öffentlich erreichbarer Produktivdienst ausgelegt.
