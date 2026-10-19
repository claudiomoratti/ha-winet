# Collaudo su stufa e migrazione

Questa procedura è da eseguire insieme all'utente: la preparazione software non
ha installato l'integrazione in Home Assistant e non ha inviato comandi alla stufa.

## 1. Preparazione

- Annotare marca/modello, temperatura visualizzata, setpoint, potenza e fase attuale.
- Salvare la configurazione attuale di Home Assistant e gli entity ID usati nelle automazioni.
- Installare l'integrazione e configurare host, divisore aria, potenza massima e tipo.
- Lasciare **Sola lettura** attiva; impostare inizialmente polling a 15 secondi.

## 2. Letture

- Confrontare aria e setpoint con il display; correggere il divisore se necessario.
- Verificare potenza 5 accessibile, nulli sconosciuti e unico dispositivo nel registro.
- Cambiare eventualmente un valore dal display della stufa e verificarne la ricezione in HA.
- Osservare un normale ciclo già previsto dall'utente, annotando codice e descrizione
  nelle varie fasi; non inferire la combustione dal solo `heat`.
- Un reload dell'integrazione deve ricreare le stesse entità e non inviare comandi.

## 3. Comandi, con utente presente

- Individuare e sospendere automazioni/scheduler precedenti che potrebbero inviare comandi.
- Disabilitare **Sola lettura** dalle opzioni soltanto quando pronti al collaudo.
- Provare una modifica del setpoint entro i limiti del modello; confrontare display e HA.
- Provare un livello di potenza supportato e controllare il risultato.
- Collaudare accensione e spegnimento soltanto durante un ciclo concordato e nel rispetto
  del manuale della stufa. Verificare che la pulizia finale rimanga riconoscibile.
- `result=true` non significa ciclo completato: attendere il riscontro del dispositivo.
- Se una chiamata va in timeout, controllare prima lo stato: non ripetere alla cieca.
- Per qualsiasi discrepanza riattivare **Sola lettura**, conservare i dettagli non sensibili
  e correggere il profilo prima di usare automazioni.

## 4. Migrazione

- Aggiornare dashboard e automazioni usando gli entity ID assegnati da HA alla nuova integrazione.
- Sostituire chiamate rest_command e helper con climate.set_temperature, climate.turn_on,
  climate.turn_off e number.set_value.
- Rimuovere il vecchio pacchetto solo dopo aver censito le sue dipendenze e validato il nuovo.
- Per tornare indietro disabilitare WiNet Local e ripristinare il pacchetto salvato;
  evitare due sistemi che comandano automaticamente la stufa contemporaneamente.

## Esito

Registrare versione dell'integrazione, HA e firmware, opzioni, fase e risultati attesi/osservati.
Non allegare token HA, risposte complete di `/api/id`, password, SSID o MAC pubblicamente.
