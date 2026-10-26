# Verifica software

## 0.2.0 — 26 ottobre 2026

Python 3.14.2, Home Assistant 2026.10.1.

| Controllo | Esito |
| --- | --- |
| pytest con fixture HA e socket esterni bloccati | 104 test superati |
| Copertura statement | 94% (528 statement, 32 non coperti) |
| Ruff lint e format | superati |
| Nuovo client contro il modulo reale, sola lettura | profilo 27436 e due velocità ricevuti |

Le nuove verifiche coprono il corpo HTTP reale delle richieste AJAX, il controllo
del profilo a ogni comando, valori mancanti o ambigui, sincronizzazione tra number
e climate, coppie di velocità, lettura immediata dopo comandi consecutivi, sola
lettura, errori parziali, timeout senza retry e traduzioni italiane del termostato.

Il collaudo hardware del protocollo è descritto in [protocol.md](protocol.md).
La scrittura della prima ventola e tutte le combinazioni nelle varie fasi della
stufa non sono ancora state certificate su hardware. Questa verifica non installa
l'integrazione sull'istanza HA dell'utente.

## 0.1.0

Eseguita il 19 ottobre 2026 su Python 3.14.8 e Home Assistant 2026.10.1.

| Controllo | Esito |
| --- | --- |
| pytest con fixture HA e socket esterni bloccati | 57 test superati |
| Copertura statement | 94% (398 statement, 25 non coperti) |
| Ruff lint | superato |
| Ruff format | superato |
| hassfest da Home Assistant 2026.10.1 | 1 integrazione, 0 non valide |
| ZIP installabile | integrità verificata |
| File destinati a Git | controllati contro token e identificativi privati raccolti |

I test coprono configurazione, duplicati MAC, riconfigurazione, opzioni, caricamento
ed unload delle entità, sola lettura, conversioni, controlli sui comandi, stati ignoti,
allarmi/pulizia, comunicazione interrotta e ripristinata, esito incerto di scrittura,
identità cambiata, dati nulli e diagnostica filtrata.

**Non è una certificazione hardware.** I comandi sono stati provati con HTTP simulato,
non sulla stufa. Nessuna modifica è stata applicata all'istanza HA dell'utente.
La validazione HACS e i workflow GitHub saranno verificati sul repository pubblicato.
