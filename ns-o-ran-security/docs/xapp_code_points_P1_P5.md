# xApp code points P1-P5 (guide section 16) — findings

Date: 2026-11-03

## TL;DR

- The running xApp (`sample-xapp-24`) is **not Go**. It is a **C++ connector**
  (`xapp-sm-connector`, binary `/usr/local/bin/hw_xapp_main`) plus a **Python agent**
  (`/home/sample-xapp/run_xapp.py`) linked by a TCP socket on `127.0.0.1:4200`.
- It is a **pass-through relay**. P1 and P5 exist; **P2, P3, P4 do not exist** in the
  baseline. There is no KPM decoding, no state, no model. The attack surface A
  (state construction) has to be *built*, not hooked into.
- The Python agent most likely drops every KPM report silently (see "Known problems" #1).
- The connector's control path cannot drive ns-3 handovers as-is (see "Known problems" #2).

Source root (host):
`~/research/nsoran/colosseum-near-rt-ric/setup/`
(`xapp-sm-connector/src/...` = C++, `sample-xapp/...` = Python)

## Data flow

```text
ns-3 gNB --E2AP/SCTP--> e2term --RMR--> hw_xapp_main (C++)
   XappRmr::xapp_rmr_receive          xapp-utils/xapp_rmr.hpp:95,123,144
   XappMsgHandler::operator()          xapp-mgmt/msgs_proc.cc:147  case RIC_INDICATION :164
   process_ric_indication()            xapp-mgmt/msgs_proc.cc:217  (E2AP APER decode only)
   procRicIndication()                 xapp-mgmt/msgs_proc.cc:245
     IE id 26 RICindicationMessage     msgs_proc.cc:272-289
       -> raw E2SM-KPM bytes (still ASN.1 encoded) copied as-is
       -> send_socket(payload, size, agent_ip)   agent_connector.cc:107
                     |
                     v  TCP 127.0.0.1:4200
Python agent  run_xapp.py:17  receive_from_socket()  xapp_control.py:30
   recv(4096) -> .decode('utf-8') -> logging.info('Received data: ...')
   (no decision, nothing sent back)

[reverse path, unused today]
Python send_socket(str)  xapp_control.py:24
   -> Xapp::handle_rx_msg_agent()      xapp.cc:222  (recv 256 B)
   -> Xapp::send_ric_control_request() xapp.cc:347
        control_msg = the raw string, no RC header
        encode_e2ap_control_request()  xapp-asn/e2ap/e2ap_control.cc
        rmr send RIC_CONTROL_REQ       xapp.cc:413
   -> e2term -> ns-3 LteEnbNetDevice::ControlMessageReceivedCallback
                                       src/lte/model/lte-enb-net-device.cc:169
```

## P1-P5 mapping

| Point | Guide meaning | Where in this xApp | Status |
|---|---|---|---|
| P1 | KPM reception callback | C++: `XappMsgHandler::operator()` `case RIC_INDICATION` (`msgs_proc.cc:164`) → `procRicIndication` (`:245`). Python: `run_xapp.py:17` loop / `receive_from_socket` (`xapp_control.py:30`) | exists |
| P2 | E2SM-KPM → SINR/PRB/thp | Nowhere. C++ decodes only the E2AP envelope; the inner `RICindicationMessage` (E2SM-KPM) is forwarded still encoded (`msgs_proc.cc:278-286`). Python treats it as UTF-8 text. | **missing** |
| P3 | KPM history → state (surface A) | Nowhere. | **missing** — to be provided by `xapp/kpm_buffer.py` + `xapp/state_builder.py` |
| P4 | state → action (N) | Nowhere. | **missing** — to be provided by `xapp/policy_wrapper.py` |
| P5 | action → E2/RC control | C++ `Xapp::send_ric_control_request` (`xapp.cc:347`), triggered by agent message (`xapp.cc:222`). ns-3 side: `ControlMessageReceivedCallback` (`lte-enb-net-device.cc:169`) expects E2SM-RC (`RicControlMessage`, TS type: ueId in header + target cell). | exists but **format-incompatible** |

## Known problems

1. **KPM probably never reaches Python.** `procRicIndication` sends binary APER bytes.
   `receive_from_socket` does `data.decode('utf-8')` and returns `''` on
   `UnicodeDecodeError`, and `run_xapp.py` then `continue`s. Binary ASN.1 almost always
   contains non-UTF-8 bytes. Consistent with this: `/home/xapp-logger.log` in the running
   container is 0 bytes (no "Received data" line ever). Also no message framing: one
   `recv(4096)` may hold a partial or several reports.
   (Not yet proven with a live run — check `docker logs` while a sim is running.)
2. **Control path is not E2SM-RC.** `send_ric_control_request` puts the agent's plain
   string into `control_msg` with an empty header; ns-3's `RicControlMessage` expects an
   E2SM-RC control header (UE id) and message (target cell). Sending as-is would at best hit
   "Unrecognized id type".
3. `GNB_ID ""` (`xapp.hpp:69`) → gNB list from R-NIB; indications are mapped to the single
   agent `AGENT_0 = 127.0.0.1` (`agent_connector.hpp:16`) by `find_agent_ip_from_gnb`.

## Options to wire the attack in (decision needed)

**Option A — Python-side xApp (recommended).**
Keep the C++ connector as transport. In Python:
P1 fix socket receive (binary, length framing) → P2 decode E2SM-KPM in Python
(asn1tools with the E2SM-KPM ASN.1 used by ns-o-ran `contrib/oran-interface`) →
P3 `kpm_buffer` + `state_builder` → P4 `policy_wrapper` → P5 send (imsi, target cell).
Needs a small C++ change: length-prefix in `send_socket`, and in
`send_ric_control_request` build a proper E2SM-RC TS message (or forward pre-encoded bytes).
Pro: our existing Python modules plug in directly; the paper's A/N split is explicit.

**Option B — Offline/file-based closed loop for the first results.**
ns-3 supports file control: `LteEnbNetDevice::ReadControlFile` (`lte-enb-net-device.cc:97`)
reads `ts_actions_for_ns3.csv` lines `timestamp,imsi,targetCellId` every 1 ms
(attribute `ControlFileName`). Combined with ns-3 file KPM traces this gives
P2 = parse trace files, P5 = write CSV, no E2 encoding at all. Fastest path to a first
aligned-vs-misaligned comparison; weaker "real O-RAN path" claim.

**Option C — Go kpimon/TS-style xApp.** The kpimon reference
(`ns-o-ran-scp-ric-app-kpimon/control/{e2sm,control}.go`) is not checked out on this
machine. Would mean adopting a different xApp; most work.
