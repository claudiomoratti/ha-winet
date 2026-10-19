# Changelog

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
