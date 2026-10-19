# Verifica software 0.1.0

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
