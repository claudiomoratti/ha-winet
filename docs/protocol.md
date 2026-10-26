# Protocollo e limiti verificati

Analisi del 19 ottobre 2026. Riferimento HASS_WINET:
`03300c8fe6b4ae87f7e81985ae830a5a559063c0`.

## Stove

La pagina API di StufaSmart documenta letture `/api/id`, `/api/global`, `/api/status`,
`/api/temperature/air`, `/api/temperature/water`, `/api/power`. Le scritture sono GET
con un valore aggiunto al percorso. Non eseguire crawler o prefetch su questi URL.

L'integrazione usa `/id` al setup e `/global` per il polling; con l'opzione ventole
P937 attiva aggiunge la lettura AJAX descritta sotto. Non conserva
la risposta completa di `/id`, che contiene anche una password AP.

I campi riconosciuti sono status, description, air, setAir, water, setWater,
power, gasflue (anche gasFlue), rpmExtractor. Campi numerici non validi restano nulli;
status non intero o risposta non-oggetto invalidano l'intero aggiornamento.

Il campione reale iniziale, letto senza comandi, aveva `status=0`, descrizione OFF,
aria e setpoint coerenti con la codifica in mezzi gradi, acqua e RPM nulli. Questa
osservazione non certifica il funzionamento in combustione o le scritture.
Non si includono qui indirizzi, MAC, SSID o risposte identificative private.

## Piazzetta P937: ventole, verifica del 26 ottobre 2026

Firmware WiNet 0.79, profilo `custom=27436`, due velocità indipendenti 1–4.
Dal pannello `management.js` sono stati ricostruiti:

- Lettura: POST `/ajax/get-registers`, corpo `key=020&category=0`.
  La risposta comprende `custom` e `params`, con coppie `[47, velocità_1]` e
  `[48, velocità_2]`.
- Scrittura: POST `/ajax/set-register`, corpo
  `key=002&memory=1&regId=47&value=3` per la prima ventola;
  `regId=48` per la seconda. Gli identificativi sono logici, non indirizzi di
  memoria fisica documentati della centralina.
- Il pannello invia il corpo con codifica form e intestazione
  `Content-Type: application/json; charset=utf-8`: il client riproduce questo formato.

Il profilo 27436 ha restituito valori coerenti con il telecomando; modifiche della
prima ventola da telecomando sono state osservate in lettura. Un comando HTTP alla
seconda ventola da 4 a 2 è stato accettato, riletto e confermato sul telecomando.
La scrittura della prima usa lo stesso meccanismo ma resta da verificare fisicamente.
Questi riscontri non certificano ogni firmware, livello o fase della stufa.

Il profilo 27437 leggeva diversamente la seconda ventola; il 27419 restituiva anche
setpoint e potenza incoerenti. Nessuno dei due è supportato. I parametri 47/48 hanno
semantiche differenti per altri profili, quindi non vanno comandati senza verifica.

La lettura generica con `custom=65535` non includeva 47/48. Le categorie 0–4
restituivano gli stessi parametri; 5–8 venivano riportate come 2. Aggiungere
`memory` e `regId` a `key=020` non ha selezionato il singolo parametro.

L'integrazione non invia `key=026` né modifica `custom`, `isOld` o `isForcedOld`.
Durante l'indagine il ripristino del profilo generico richiedeva `customCode=0`;
`65535` era ignorato. Dopo il ripristino `isOld` risultava false, senza perdita
delle letture principali. Il significato preciso dei flag non è documentato.

Con l'opzione P937 attiva si leggono i registri a ogni polling. Un errore di questo
endpoint lascia disponibili i dati principali ma non le velocità; prima di ogni
scrittura vengono comunque rilette velocità e profilo. I comandi delle due ventole
sono serializzati con il polling e seguiti da riscontro immediato. Una coppia non
è atomica: in caso di errore parziale viene letto lo stato reale senza retry.

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
