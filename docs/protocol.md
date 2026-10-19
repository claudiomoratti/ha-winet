# Protocollo e limiti verificati

Analisi del 19 ottobre 2026. Riferimento HASS_WINET:
`03300c8fe6b4ae87f7e81985ae830a5a559063c0`.

## Stove

La pagina API di StufaSmart documenta letture `/api/id`, `/api/global`, `/api/status`,
`/api/temperature/air`, `/api/temperature/water`, `/api/power`. Le scritture sono GET
con un valore aggiunto al percorso. Non eseguire crawler o prefetch su questi URL.

L'integrazione usa soltanto `/id` al setup e `/global` per il polling. Non conserva
la risposta completa di `/id`, che contiene anche una password AP.

I campi riconosciuti sono status, description, air, setAir, water, setWater,
power, gasflue (anche gasFlue), rpmExtractor. Campi numerici non validi restano nulli;
status non intero o risposta non-oggetto invalidano l'intero aggiornamento.

Il campione reale iniziale, letto senza comandi, aveva `status=0`, descrizione OFF,
aria e setpoint coerenti con la codifica in mezzi gradi, acqua e RPM nulli. Questa
osservazione non certifica il funzionamento in combustione o le scritture.
Non si includono qui indirizzi, MAC, SSID o risposte identificative private.

## Blower Cube: dispositivo distinto

`README_OTHER` del repository di riferimento presenta X3 Relay e Blower Cube come
prodotti separati. Il file `Other works/packages/winet_blower_pkg.yaml` usa
`input_text.valore_ip_locale_blower`, anziché l'host Stove.

Le sue letture `/api/global` prevedono fan1, fan2 e fan3. Il package mostra
comandi per manualSpeed, modeAuto, setAir, deltaT, min, max e useTsense tramite
`/api/fan/{indice}/...`, oltre a season. Non sono endpoint documentati della Stove.
La semantica esatta, le unità e la capacità di interrompere una ventola in modalità
automatica richiedono documentazione o un dispositivo Blower Cube di prova.

Un futuro supporto Blower dovrebbe avere riconoscimento del modello, configurazione
separata, entità native fan/number/select e test dedicati. Non abilitare questi comandi
su un modulo Stove per tentativi.

## Cosa manca per dichiarare compatibilità hardware

- Marca, modello e firmware della stufa; capacità reali, intervalli e passi supportati.
- Conferma del divisore tramite display, separatamente da quello che calcola il package.
- Sequenza letta durante avvio, lavoro, modulazione/standby e pulizia finale.
- Esiti reali dei setpoint e della potenza, con una variazione alla volta.
- Stato di allarme osservato naturalmente o su simulatore: non provocare un guasto.

Le transizioni note dal package sono un profilo iniziale, non un elenco universale
per tutte le centraline. Il codice conserva gli stati non riconosciuti.
