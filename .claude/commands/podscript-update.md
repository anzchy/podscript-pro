# Podscript Update & Deploy

When this command is invoked, execute the following deployment workflow:

## Step 1: Commit Local Changes to Master

```bash
# Check current git status
git status

# If there are changes, add and commit them
git add -A
git commit -m "<generate appropriate commit message based on changes>"

# If not on master, checkout master and merge
git checkout master
git merge <current-branch> --no-edit

# Push to remote
git push origin master
```

## Step 2: SSH to Production Server

Connect to the server:
- Host: `66.154.105.210`
- User: `lighthouse`
- Password: `511882?Chy`

## Step 3: Stop Podscript Process

```bash
# Find and kill uvicorn process
pkill -f "uvicorn podscript_api.main:app" || true
```

## Step 4: Pull Latest Code

```bash
cd ~/podscript/podscript-pro
git fetch origin
git reset --hard origin/master
```

## Step 5: Restart Podscript Service

```bash
cd ~/podscript/podscript-pro
source .venv/bin/activate
PYTHONPATH=./src nohup python -m uvicorn podscript_api.main:app --host 0.0.0.0 --port 8001 > nohup.out 2>&1 &
```

## Step 6: Verify Deployment

```bash
# Wait for service to start
sleep 3

# Check if process is running
ps aux | grep uvicorn | grep -v grep

# Test the API endpoint
curl -s https://podscript.jackcheng.tech/api/auth/me | head -c 100
```

## Important Notes

- Always show git diff before committing to let user review changes
- Generate meaningful commit messages based on the actual changes
- If there are no local changes, skip Step 1 and proceed directly to deployment
- Report success/failure status after each step
