"""Static shell-completion script generators for the `openalex` CLI.

Completion is word-list based (subcommand names + global flags), not a full
argparse-aware completer — that's enough for a ~10-subcommand tool and avoids
an extra dependency (argcomplete) just for this.
"""

GLOBAL_FLAGS = [
    "--format", "-f", "--output", "-o", "--quiet", "-q", "--no-color",
    "--refresh", "--no-cache", "--api-key", "--email", "--version", "--help", "-h",
]


def bash_script(prog: str, commands: list[str]) -> str:
    cmd_list = " ".join(commands)
    return f"""\
# {prog} bash completion — add to ~/.bashrc:
#   eval "$({prog} completion bash)"
_{prog}_completions() {{
    local cur
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "{cmd_list}" -- "$cur") )
    fi
}}
complete -F _{prog}_completions {prog}
"""


def zsh_script(prog: str, commands: list[str]) -> str:
    cmd_lines = "\n".join(f"        '{c}'" for c in commands)
    return f"""\
#compdef {prog}
# {prog} zsh completion — add to ~/.zshrc:
#   eval "$({prog} completion zsh)"
_{prog}() {{
    local -a subcmds
    subcmds=(
{cmd_lines}
    )
    if (( CURRENT == 2 )); then
        _describe 'command' subcmds
    fi
}}
_{prog}
"""


def powershell_script(prog: str, commands: list[str]) -> str:
    cmd_list = ", ".join(f"'{c}'" for c in commands)
    return f"""\
# {prog} PowerShell completion — add to your $PROFILE:
#   {prog} completion powershell | Out-String | Invoke-Expression
Register-ArgumentCompleter -Native -CommandName {prog} -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    @({cmd_list}) | Where-Object {{ $_ -like "$wordToComplete*" }} |
        ForEach-Object {{ [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }}
}}
"""


GENERATORS = {
    "bash": bash_script,
    "zsh": zsh_script,
    "powershell": powershell_script,
}


def generate(shell: str, prog: str, commands: list[str]) -> str:
    return GENERATORS[shell](prog, commands)
