## 🔄 Updating from the Template

This project was bootstrapped with [WoosterTech/simple-modern-uv](https://github.com/WoosterTech/simple-modern-uv), which uses [Copier](https://copier.readthedocs.io/).

You can pull in updates from the template at any time:

``` bash
# Make sure copier is installed
uv tool install copier

# Run the update
copier update --trust
```

## 🛡️ Recommended Git workflow

1. **Commit or stash your changes** before updating:
    ``` bash
    git add .
    git commit -m "WIP before template update"
    # or stash if you don't want to commit
    git stash
    ```
1. **Run the update:**

    `copier update --trust`
1. **Review the changes** with Git:

    `git diff`

    Copier may show you diffs interactively as well, but `git diff` (or your favorite GUI) gives a clear overview.
1. **Test your project** after updating -- sometimes template changes require tweaks in your code.
1. **Commit the update** once you're happy:
    ``` bash
    git add .
    git commit -m "Update from template"
    ```

## 🔍 Preview mode

If you want to see what would change without touching files:

`copier update --trust --pretend`
