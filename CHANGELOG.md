# Changelog

## 0.4.0 — 2026-10-27

- Nuovo sensore P937 della fase operativa dettagliata, con codici grezzi conservati:
  spenta, attesa fiamma, accensione, lavoro, standby, pulizie e allarmi.
- Nuove diagnostiche del modulo: RSSI in dBm, stato Wi-Fi, stato cloud, ultima causa
  di disconnessione e ultimo errore cloud; firmware mostrato nelle informazioni dispositivo.
- Codice allarme grezzo disponibile come diagnostica, senza inventare descrizioni non
  documentate dal produttore.
- Le letture ausiliarie restano isolate: un errore della pagina diagnostica non rende
  indisponibile il termostato né provoca scritture o tentativi automatici.
- Confermata sul P937 reale la transizione `2` (attesa fiamma) → `4` (lavoro); le
  velocità 47/48 sono setpoint e non feedback di rotazione.

## 0.3.0 — 2026-10-27

- Nuove entità diagnostiche P937 per livello del segnale Wi-Fi, profilo WiNet e
  modalità della gestione automatica interna.
- Validazione stretta dei nuovi valori: dati assenti, fuori intervallo o con tipo
  errato restano sconosciuti e non compromettono il termostato principale.
- Nessuna richiesta di rete aggiuntiva: le diagnostiche riusano la lettura AJAX
  già effettuata quando il supporto alle due ventole è abilitato.

## 0.2.0 — 2026-10-26

- Supporto opzionale delle due ventole Piazzetta P937, livelli 1–4, con profilo
  WiNet 27436 già configurato sul modulo.
- Selettore nativo della coppia di velocità nel termostato, tradotto in italiano
  e inglese, più due controlli number separati.
- Lettura dei parametri logici 47/48 tramite AJAX, verifica del profilo prima di
  scrivere e riscontro immediato condiviso fra tutte le entità.
- Rispetto della sola lettura, blocco di valori o profili non supportati e nessun
  tentativo automatico di ripetere una scrittura, anche in caso di esito parziale.
- Profilo del modulo e modalità di protocollo non vengono modificati dall'integrazione.

## 0.1.1 — 2026-10-26

- Potenza disponibile come preimpostazione dell'entità climate, nella stessa scheda
  termostato di temperatura e accensione, senza componenti frontend aggiuntivi.
- Livelli 1–5 o 1–9 secondo la configurazione, con etichette in italiano e inglese.
- Preimpostazione letta dal dispositivo e sincronizzata con il controllo number;
  la selezione modifica solo la potenza, mantenendo i controlli di sola lettura.

## 0.1.0 — 2026-10-19

Prima versione sperimentale per WiNet Stove locale.

- Config flow, opzioni e riconfigurazione host con verifica MAC.
- Entità climate, number, sensor e binary_sensor, con supporto idro opzionale.
- Conversione aria selezionabile e potenza massima 5/9.
- Polling coordinato, indisponibilità e nulli preservati.
- Modalità iniziale sola lettura, validazione comandi e nessun retry di scrittura.
- Italiano/inglese, diagnostica filtrata, test HA e struttura HACS.

Limiti: comandi e mappa stati non-OFF ancora da collaudare su hardware;
Blower Cube, ventole Stove, cloud e programmazione interna non supportati.
