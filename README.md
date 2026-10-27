# WiNet Local for Home Assistant

Integrazione custom per le **API locali WiNet Stove**, preparata per HACS.
Versione **0.4.0**, sperimentale: test software su Home Assistant **2026.10.1**.
Ventole collaudate su Piazzetta P937 con WiNet 0.79 e profilo 27436;
setpoint, potenza, accensione e spegnimento richiedono ancora un collaudo completo.

## Entità native

- **Climate**: temperatura aria, setpoint, modalità `heat` / `off`, accensione e spegnimento,
  preimpostazioni di potenza da 1 a 5 (fino a 9 sui modelli compatibili).
- **Number**: potenza da 1 a 5, oppure fino a 9 se il modello lo supporta.
- **Sensor**: stato, descrizione originale, temperatura aria, fumi, giri estrattore.
- **Diagnostica P937**: fase operativa dettagliata, codice allarme grezzo, RSSI,
  stato Wi-Fi/cloud, ultime cause di errore, firmware, profilo e gestione automatica.
- **Binary sensor**: allarme secondo la mappa stati convenzionale WiNet.
- **Idro opzionale**: temperatura acqua e setpoint acqua 40–80 °C.
- **Due ventole P937 opzionali**: velocità indipendenti 1–4 e selettore della coppia
  di velocità direttamente nel termostato.

Un unico dispositivo, identificato dal MAC, raggruppa tutte le entità. Più moduli
possono essere aggiunti senza collisioni. Interfaccia e opzioni in italiano e inglese.
Nessuna dashboard o integrazione frontend aggiuntiva è necessaria.

### Potenza nella scheda termostato

La potenza è disponibile anche come preimpostazione dell'entità climate:
**Potenza 1**, **Potenza 2**, …, fino al massimo configurato nell'integrazione.
Per mostrarla nella stessa scheda di temperatura e accensione, aggiungere la funzione
**Preimpostazioni climatizzatore** nell'editor della scheda termostato, oppure usare:

```yaml
type: thermostat
entity: climate.nome_della_stufa
features:
  - type: climate-hvac-modes
  - type: climate-preset-modes
    style: dropdown
```

Sostituire l'entity ID con quello della propria stufa. Il selettore mostra il livello
letto dal dispositivo e resta sincronizzato con l'entità number e con l'app WiNet.
Selezionare una potenza modifica soltanto quel valore: non accende la stufa e non
cambia la temperatura impostata. Le azioni standard usano `climate.set_preset_mode`
con `preset_mode: power_1` … `power_5` (o `power_9` se configurato).

### Due ventole nella scheda termostato

Per la **Piazzetta P937**, attivare **Due ventole Piazzetta P937 (profilo WiNet 27436)**
nelle opzioni dell'integrazione. Il modulo deve avere già attivo il profilo **27436**:
l'integrazione lo verifica a ogni comando, ma non lo imposta né cambia il protocollo.
Il supporto è disattivato per impostazione predefinita sulle installazioni esistenti.

Il termostato offre un solo selettore nativo di ventilazione: mostra le 16 coppie
**V1: 1 · V2: 1** … **V1: 4 · V2: 4**. Aggiungere la funzione **Modalità ventola
climatizzatore** alla scheda, oppure usare:

```yaml
type: thermostat
entity: climate.nome_della_stufa
features:
  - type: climate-hvac-modes
  - type: climate-preset-modes
    style: dropdown
  - type: climate-fan-modes
    style: dropdown
```

L'azione `climate.set_fan_mode` accetta `fan_mode: fans_3_2`, per esempio, per impostare
ventola 1 a 3 e ventola 2 a 2. Due entità **number**, **Ventola 1** e **Ventola 2**,
permettono anche regolazioni separate da 1 a 4 con `number.set_value`.
Non sono previste velocità 0, spegnimento delle ventole o modalità automatica.

Tutti i controlli leggono gli stessi dati, recepiscono le modifiche dal telecomando
e rispettano **Sola lettura**. Un comando modifica solo le velocità richieste che
risultano diverse, poi le rilegge immediatamente. Una coppia richiede fino a due
scritture: se la seconda fallisce, la prima può essere già applicata; viene segnalato
l'errore e letto lo stato reale, senza ripetere i comandi.

## Installazione con HACS

Repository: **https://github.com/claudiomoratti/ha-winet**

1. HACS → menu → **Repository personalizzati**.
2. Aggiungere l'URL di questo repository, categoria **Integrazione**.
3. Scaricare **WiNet Local** e riavviare Home Assistant.
4. Impostazioni → Dispositivi e servizi → Aggiungi integrazione → **WiNet Local**.

La compatibilità con i repository personalizzati HACS non implica inclusione
nell'elenco predefinito HACS o approvazione ufficiale Home Assistant.

### Installazione manuale

Copiare la cartella `custom_components/winet` in `/config/custom_components/winet`
e riavviare Home Assistant. Non copiare `tests`, `docs` o file di sviluppo in `/config`.

## Configurazione

| Opzione | Default | Significato |
| --- | --- | --- |
| Host | richiesto | IP o hostname del WiNet, anche con porta; senza `http://` |
| Divisore aria | 2 | `2`: API in mezzi gradi; `1`: API in °C |
| Potenza massima | 5 | Selezionare 9 solo per modelli compatibili |
| Idro | no | Crea sensore e setpoint acqua |
| Due ventole P937 | no | Controlli 1–4 per entrambe le ventole, solo con profilo 27436 |
| Sola lettura | sì | Blocca tutte le scritture, incluse le azioni HA |
| Intervallo | 15 s | Polling condiviso, configurabile 10–300 s; il profilo P937 aggiunge registri e diagnostica modulo |

Le opzioni sono modificabili dall'integrazione; vengono applicate con un reload.
**Riconfigura** cambia l'indirizzo verificando che il MAC corrisponda allo stesso dispositivo.
Non serve un token Home Assistant: il componente comunica direttamente con WiNet in LAN.

### Verificare la scala delle temperature

La documentazione pubblica mostra °C diretti, mentre il pacchetto HASS_WINET usa
mezzi gradi. Il default `2` riproduce quest'ultimo comportamento, ma non è un
riconoscimento automatico del firmware. Confrontare sempre con il display:
`setAir=38` corrisponde a 19 °C con divisore 2, a 38 °C con divisore 1.
La conversione è applicata sia in lettura sia in scrittura, solo all'aria.
Il setpoint aria esposto è 5–40 °C, passo 0,5 °C; la compatibilità del passo con
ogni modello va verificata durante il collaudo. Acqua: passo 1 °C, nessuna divisione.

## Comportamento

Il componente nasce in sola lettura. I controlli restano visibili; le azioni di
scrittura danno un errore esplicito finché questa opzione è attiva.

- Polling condiviso asincrono; nessuna lettura di rete dalle proprietà delle entità.
- Timeout, HTTP non validi e risposte malformate rendono il dispositivo indisponibile.
- Valori `null` rimangono sconosciuti, senza convertirli in zero. I fumi a 0 °C sono
  conservati così come riportati: non costituiscono una misura validata del sensore.
- Un errore degli endpoint ausiliari rende sconosciuti solo ventole o diagnostiche;
  il termostato mantiene le letture principali.
- I comandi sono serializzati, non vengono ritentati automaticamente e sono seguiti
  da una lettura. `result=true` significa accettazione, non completamento del ciclo.
- Un timeout di scrittura ha esito incerto: verificare lo stato prima di riprovare.
- Prima di accendere si rilegge lo stato: l'avvio è consentito soltanto da `0`;
  da `1` non viene inviato un altro comando. Pulizia, allarmi e stati ignoti bloccano l'avvio.
- Lo spegnimento resta richiedibile con connessione disponibile anche durante un allarme.
- Setup, reload e riavvio non inviano comandi e non ripristinano vecchi setpoint.
- Le modifiche dal display o dall'app WiNet vengono recepite al polling successivo.

### Mappa stati: compatibilità da verificare

La mappa deriva dal pacchetto HASS_WINET, non da una specifica completa del costruttore:

| Codice | Sensore stato | Modalità climate | Allarme |
| --- | --- | --- | --- |
| 0 | Spenta | off | no |
| 1 | Accesa | heat | no |
| 2 | Pulizia finale | off | no |
| 3 | Allarme | sconosciuta | sì |
| 4 | Non gestita | sconosciuta | sconosciuto |
| altro | Non riconosciuto | sconosciuta | sconosciuto |

La modalità `off` durante pulizia non significa che ventole e combustione siano
immediatamente ferme. Il sensore di stato mantiene visibile la fase reale.
`hvac_action` è deliberatamente assente: con i dati disponibili non si distingue
in modo universale accensione, combustione, modulazione e standby. Non si deducono
queste fasi da temperature, RPM o parole nella descrizione.

Sul profilo P937 27436 è disponibile anche **Fase operativa**, separata dallo stato
generico sopra: codici WiNet 0–9 per spenta, attesa fiamma, accensione, lavoro,
standby, pulizie e allarmi. Il codice grezzo resta visibile come attributo. Le velocità
ventola sono setpoint e non provano che i motori stiano girando; non viene quindi
generato un sensore di rotazione stimato.

L'integrazione lascia la regolazione alla centralina della stufa. Non implementa
un termostato esterno con cicli accendi/spegni o una programmazione interna.
Le automazioni HA possono chiamare i servizi standard `climate` e `number`, dopo
il collaudo e considerando i tempi previsti dal produttore.

## Ventole e Blower Cube

Nel repository di riferimento le API `/api/fan/...` appartengono al **WiNet Blower Cube**,
configurato con un proprio host. Il supporto P937 usa invece l'interfaccia AJAX del
**WiNET Gen.Stove**, con profilo 27436 e parametri logici 47/48. Non usa le API
Blower Cube e non scambia i giri dell'estrattore fumi per una velocità regolabile.
Vedere [analisi del protocollo](docs/protocol.md).

## Primo collaudo e migrazione

Seguire [la procedura di test](docs/testing.md). La prima verifica avviene in sola
lettura; prima dei test di comando individuare e sospendere le automazioni del
vecchio pacchetto che possono comandare la stufa. Il componente non rimuove il
pacchetto precedente né migra automaticamente gli entity ID.

## Diagnostica e privacy

`/api/id` può contenere la password Wi-Fi dell'access point: il client conserva
soltanto modello e MAC. La diagnostica esporta opzioni e valori numerici noti,
escludendo host, MAC, SSID, password e descrizioni libere. Nessun token, snapshot
personale o dato della rete domestica è incluso in questo repository.

## Sviluppo

Python 3.14, Home Assistant 2026.10.1:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest --cov=custom_components.winet
```

I test usano le fixture Home Assistant e HTTP simulato, con socket esterni disabilitati.
La CI comprende test, Ruff, hassfest e validazione HACS.
Vedere [risultati della validazione locale](docs/validation.md); i workflow remoti
sono verifiche aggiuntive eseguite sul repository pubblicato.

## Riferimenti

Implementazione originale, senza riuso del codice o delle immagini del pacchetto:

- [API locali StufaSmart](https://stufasmart.it/documentazione-tecnica/api-in-locale/)
- [HASS_WINET di morenonew2](https://github.com/morenonew2/HASS_WINET), riferimento di compatibilità
- [Entità Climate HA](https://developers.home-assistant.io/docs/core/entity/climate/)
- [Requisiti integrazioni HACS](https://www.hacs.xyz/docs/publish/integration/)

Progetto indipendente, non affiliato a WiNet, StufaSmart o Home Assistant.
Licenza MIT.
