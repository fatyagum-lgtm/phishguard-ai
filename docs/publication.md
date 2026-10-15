# Publishing after local review

No Git repository, commit, remote or push was created during this build. Review
README, license, screenshots and `reports/demo/` before publication. Only synthetic
messages are bundled; real dataset error examples are defanged and attributed.
The raw dataset, virtual environments, Node dependencies and build output are ignored.

If you decide to publish, create an empty GitHub repository named `phishguard-ai`
in your account using GitHub's UI, then run these commands yourself from this root:

```bash
git init -b main
git add .
git status --short
git diff --cached --stat
git commit -m "Build offline phishing investigation and research platform"
git remote add origin https://github.com/YOUR_ACCOUNT/phishguard-ai.git
git push -u origin main
```

Replace `YOUR_ACCOUNT` with your account. Inspect staged contents before committing;
do not add private messages or raw data. The workflow uses Node 24 based official
GitHub Actions. Check its real run in the Actions tab after pushing; do not add a
success badge until a hosted run has actually succeeded. Enable private vulnerability
reporting if desired and review dependency updates before adopting them.
