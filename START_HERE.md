# START HERE

## One command

```bash
git clone https://github.com/brandonbrown15/Autocode.git
cd Autocode
./start
```

Answer a few questions. Wait. Done.

---

## What you need before `./start`

1. **GitHub account**  
   Easy path: make a token at https://github.com/settings/tokens?type=beta  
   (Contents + Pull requests = Read and write)

2. **Notion account** (free is fine)  
   - Make an integration: https://www.notion.so/my-integrations  
   - Make a blank page named **Autocode Hub**  
   - On that page: **••• → Connections → Autocode**  
   - Copy the page link

3. **This computer turned on** (Jetson or Linux)

Optional: a big SSD (like 4TB). `./start` will try to use it automatically.

---

## After setup

| Do this | Command |
|---------|---------|
| See if it is healthy | `./scripts/doctor.sh` |
| See what it is doing | `./scripts/status.sh` |
| Pause it | `./scripts/control.sh pause` |
| Add work | Notion → Build Queue → Status = **Ready** |

Keep the first tasks tiny (fix typos, small docs).

---

## Stuck?

```bash
./scripts/doctor.sh
```

Read the **FAIL** lines. Fix those. Run `./start` again.

More detail: [docs/go-live.md](docs/go-live.md)
