# Lab 1.3: RESTCONF with YANG Models Using Bruno

**Blueprint objective:** CCNP AUTOCOR 350-901, Objective 1.3

Builds, changes and removes a Loopback interface on a Cisco Catalyst 8000V using RESTCONF requests defined in a Bruno collection. The YANG model (`Cisco-IOS-XE-native`) determines the JSON payload structure.

> **Lab use only.** Runs against a CML node. No production devices, addresses or credentials are included.

## What this lab demonstrates

- Enabling RESTCONF on IOS XE
- Reading YANG module data from the device with GET
- Creating (PUT), modifying (PATCH) and deleting (DELETE) a Loopback interface
- Validating results with Bruno assertions and device `show` commands
- Keeping credentials out of Git using a Bruno secret environment variable
- Running the same collection from the command line with the Bruno CLI

## Prerequisites

| Item | Detail |
|------|--------|
| Device | Cisco Catalyst 8000V in CML, reachable on its management IP |
| Tools | Bruno 2.13 (GUI), Bruno CLI (`@usebruno/cli`), cURL |
| Device user | Privilege 15 account, for example `labadmin` |

### Device configuration

```
conf t
 username labadmin privilege 15 secret <password>
 restconf
 ip http secure-server
 ip http authentication local
 end
write memory
```

If `aaa new-model` is enabled, also add `aaa authentication login default local` and `aaa authorization exec default local`.

## Folder layout

```
restconf-yang/
├── README.md
├── bruno.json
├── collection.bru              # Collection-level auth (Basic) and headers
├── environments/               # Git-ignored (see Security notes)
│   └── lab.bru
├── environments-example/
│   └── lab.bru                 # Placeholder values only
├── 01-get-modules.bru
├── 02-get-native-hostname.bru
├── 03-put-loopback100.bru
├── 04-patch-loopback100.bru
├── 05-delete-loopback100.bru
└── loopback.json               # Payload for the cURL cross-check
```

Adjust the request names above to match what is in your collection.

## Setup

1. In Bruno, open the `restconf-yang` folder as a collection.
2. Create an environment named `lab` with these variables:

   | Variable | Value | Secret |
   |----------|-------|--------|
   | `host` | 8000V management IP | no |
   | `username` | RESTCONF user | no |
   | `password` | device password | **yes** |

3. Select `lab` as the active environment.
4. Set the collection Auth to **Basic** with `{{username}}` and `{{password}}`.
5. Set collection headers:
   - `Accept: application/yang-data+json`
   - `Content-Type: application/yang-data+json`
6. For a lab device with a self-signed certificate, turn off SSL certificate verification in Bruno Preferences.

## Requests

Base URL: `https://{{host}}/restconf/data`

| # | Method | Path | Expected result |
|---|--------|------|-----------------|
| 1 | GET | `/ietf-yang-library:modules-state` | 200, list of supported YANG modules |
| 2 | GET | `/Cisco-IOS-XE-native:native/hostname` | 200, device hostname |
| 3 | PUT | `/Cisco-IOS-XE-native:native/interface/Loopback=100` | 201 (created) or 204 (replaced) |
| 4 | PATCH | `/Cisco-IOS-XE-native:native/interface/Loopback=100` | 204 |
| 5 | DELETE | `/Cisco-IOS-XE-native:native/interface/Loopback=100` | 204 |

### Request 3 body (PUT)

```json
{
  "Cisco-IOS-XE-native:Loopback": {
    "name": 100,
    "description": "RESTCONF-BRUNO-LAB",
    "ip": {
      "address": {
        "primary": {
          "address": "10.100.0.1",
          "mask": "255.255.255.255"
        }
      }
    }
  }
}
```

### Request 4 body (PATCH)

```json
{
  "Cisco-IOS-XE-native:Loopback": {
    "name": 100,
    "description": "CHANGED-VIA-BRUNO"
  }
}
```

## Verification

On the 8000V after each change:

```
show running-config interface Loopback100
show ip interface brief | include Loopback100
```

Expected after request 3: Loopback100 is up with `10.100.0.1/32` and the description `RESTCONF-BRUNO-LAB`.
Expected after request 4: the description reads `CHANGED-VIA-BRUNO`.
Expected after request 5: Loopback100 no longer exists.

In Bruno, the **Assert** tab on each request checks the status code, and the **Runner** executes the whole collection in order.

## Command-line run

The `password` secret is not stored in the repo, so pass it from the shell:

```bash
cd restconf-yang
export LAB_PW='<device password>'
bru run --env lab --env-var password=$LAB_PW --insecure
```

`--insecure` skips certificate verification and is for lab devices only.

## cURL cross-check

Bruno's **Generate Code** feature produces equivalent cURL. For example:

```bash
curl -k -u labadmin:"$LAB_PW" \
  -H "Content-Type: application/yang-data+json" \
  -X PUT https://<ip>/restconf/data/Cisco-IOS-XE-native:native/interface/Loopback=100 \
  -d @loopback.json
```

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| 401 Unauthorized | Wrong credentials, `lab` environment not selected, or `{{password}}` not resolving. Check the Timeline tab. |
| 403 Forbidden | User is not privilege 15, or AAA authorization is missing |
| Connection refused / timeout | `restconf` or `ip http secure-server` missing, or the IP is wrong |
| Certificate error | Self-signed cert: disable SSL verification (lab only) |
| 400 / 404 on PUT | JSON field names do not match the model. Compare against the GET output from request 2. |

## Security notes

- `environments/` is listed in `.gitignore`. The `password` variable is a Bruno secret and is never written to the `.bru` file.
- Use `environments-example/lab.bru` as a template and keep real values local.
- Only lab addresses and test credentials are used here.

## Takeaways

- YANG models define the exact structure of the JSON that RESTCONF accepts.
- PUT replaces a resource, PATCH merges into it, DELETE removes it.
- A request collection kept in Git makes API changes repeatable, reviewable and runnable in a pipeline.
