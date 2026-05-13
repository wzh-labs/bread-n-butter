#!/usr/bin/env bash

alias ga="git add"
alias gas="gh auth switch"
alias gb="git branch"
alias gbd="git branch -D"
alias gbdr="git push origin --delete"
alias gc="git commit"
alias gcm="git commit -m"
alias gco="git checkout"
alias gd="git diff"
alias gdhm="gd head main"
alias gds="git diff --staged"
alias gf="git fetch"
alias gl="git log"
alias glo="git log --oneline"
alias gp="git pull"
alias gpom="gp origin main"
alias gpu="git push"
alias gpu2="gas && gpu && gas"
alias gr="git restore"
alias gs="git status"
alias gst="git stash"
alias gsw="git switch"
alias m="gco main && gp"

gsm() {
  if [ -z "$1" ]; then
    echo "Usage: gsm <branch-name>"
    return 1
  fi
  local branch="$1"
  git checkout main && git pull || return 1
  git checkout "$branch" && git pull origin main --no-edit || return 1
  git diff HEAD main
  if [ -z "$(git diff HEAD main)" ]; then
    git checkout main
    git branch -D "$branch"
  fi
}
