# AL-MUKH Global Map
> Auto-generated: 2026-07-25 15:01:56

---

## Spoke Network

```mermaid
graph TD
    ALMUKH["AL-MUKH<br/>Master Vault<br/>Docs: 0"]

    al_mukh_vault["al-mukh-vault<br/>3 files<br/>🟢 healthy"]
    ALMUKH --> al_mukh_vault
    obsidian_vault["obsidian-vault<br/>17 files<br/>🟢 healthy"]
    ALMUKH --> obsidian_vault
```

---

## Spoke Details

| Spoke | Path | Files | Size | Status | Last Modified |
|-------|------|-------|------|--------|---------------|
| `al-mukh-vault` | `/home/kali/AL-MUKH` | 3 | 8.3 KB | 🟢 healthy | 2026-07-25 11:20 |
| `obsidian-vault` | `/home/kali/Documents/Obsidian Vault` | 17 | 137.5 KB | 🟢 healthy | 2026-07-25 14:46 |

---

## Namespace Hierarchy

```mermaid
graph LR
    subgraph Master Vault
        ROOT[AL-MUKH]
        docs[docs]
        ROOT --> docs
        systemd[systemd]
        ROOT --> systemd
    end
    ROOT -.-> al_mukh_vault
    ROOT -.-> obsidian_vault
```
