"""This module generates and formats instructional messages about fixing Markdown code blocks."""

import logging
from typing import Optional

from . import parsing

log = logging.getLogger(__name__)

_EXAMPLE_PY = "{lang}\nprint('Hello, world!')"  # Make sure to escape any Markdown symbols here.
_EXAMPLE_CODE_BLOCKS = (
    "\\`\\`\\`{content}\n\\`\\`\\`\n\n"
    "**This will result in the following:**\n"
    "```{content}```"
)


def _get_example(language: str) -> str:
    """Return an example of a correct code block using `language` for syntax highlighting."""
    # Determine the example code to put in the code block based on the language specifier.
    if language.lower() in parsing.PY_LANG_CODES:
        log.trace(f"Code block has a Python language specifier `{language}`.")
        content = _EXAMPLE_PY.format(lang=language)
    elif language:
        log.trace(f"Code block has a foreign language specifier `{language}`.")
        # It's not feasible to determine what would be a valid example for other languages.
        content = f"{language}\n..."
    else:
        log.trace("Code block has no language specifier.")
        content = "\nHello, world!"

    return _EXAMPLE_CODE_BLOCKS.format(content=content)


def _get_bad_ticks_message(code_block: parsing.CodeBlock) -> Optional[str]:
    """Return instructions on using the correct ticks for `code_block`."""
    log.trace("Creating instructions for incorrect code block ticks.")

    valid_ticks = f"\\{parsing.BACKTICK}" * 3
    instructions = (
        "It looks like you are trying to paste code into this channel.\n\n"
        "You seem to be using the wrong symbols to indicate where the code block should start. "
        f"The correct symbols would be {valid_ticks}, not `{code_block.tick * 3}`."
    )

    log.trace("Check if the bad ticks code block also has issues with the language specifier.")
    addition_msg = _get_bad_lang_message(code_block.content)
    if not addition_msg and not code_block.language:
        addition_msg = _get_no_lang_message(code_block.content)

    # Combine the back ticks message with the language specifier message. The latter will
    # already have an example code block.
    if addition_msg:
        log.trace("Language specifier issue found; appending additional instructions.")

        # The first line has double newlines which are not desirable when appending the msg.
        addition_msg = addition_msg.replace("\n\n", " ", 1)

        # Make the first character of the addition lower case.
        instructions += "\n\nFurthermore, " + addition_msg[0].lower() + addition_msg[1:]
    else:
        log.trace("No issues with the language specifier found.")
        example_blocks = _get_example(code_block.language)
        instructions += f"\n\n**Here is an example of how it should look:**\n{example_blocks}"

    return instructions


def _get_no_ticks_message(content: str) -> Optional[str]:
    """If `content` is Python/REPL code, return instructions on using code blocks."""
    log.trace("Creating instructions for a missing code block.")

    if parsing.is_repl_code(content) or parsing.is_python_code(content):
        example_blocks = _get_example("python")
        return (
            "It looks like you're trying to paste code into this channel.\n\n"
            "Discord has support for Markdown, which allows you to post code with full "
            "syntax highlighting. Please use these whenever you paste code, as this "
            "helps improve the legibility and makes it easier for us to help you.\n\n"
            f"**To do this, use the following method:**\n{example_blocks}"
        )
    else:
        log.trace("Aborting missing code block instructions: content is not Python code.")


def _get_bad_lang_message(content: str) -> Optional[str]:
    """
    Return instructions on fixing the Python language specifier for a code block.

    If `code_block` does not have a Python language specifier, return None.
    If there's nothing wrong with the language specifier, return None.
    """
    log.trace("Creating instructions for a poorly specified language.")

    info = parsing.parse_bad_language(content)
    if not info:
        log.trace("Aborting bad language instructions: language specified isn't Python.")
        return

    lines = []
    language = info.language

    if info.leading_spaces:
        log.trace("Language specifier was preceded by a space.")
        lines.append(f"Make sure there are no spaces between the back ticks and `{language}`.")

    if not info.terminal_newline:
        log.trace("Language specifier was not followed by a newline.")
        lines.append(
            f"Make sure you put your code on a new line following `{language}`. "
            f"There must not be any spaces after `{language}`."
        )

    if lines:
        lines = " ".join(lines)
        example_blocks = _get_example(language)

        # Note that _get_bad_ticks_message expects the first line to have two newlines.
        return (
            f"It looks like you incorrectly specified a language for your code block.\n\n{lines}"
            f"\n\n**Here is an example of how it should look:**\n{example_blocks}"
        )
    else:
        log.trace("Nothing wrong with the language specifier; no instructions to return.")


def _get_no_lang_message(content: str) -> Optional[str]:
    """
    Return instructions on specifying a language for a code block.

    If `content` is not valid Python or Python REPL code, return None.
    """
    log.trace("Creating instructions for a missing language.")

    if parsing.is_repl_code(content) or parsing.is_python_code(content):
        example_blocks = _get_example("python")

        # Note that _get_bad_ticks_message expects the first line to have two newlines.
        return (
            "It looks like you pasted Python code without syntax highlighting.\n\n"
            "Please use syntax highlighting to improve the legibility of your code and make "
            "it easier for us to help you.\n\n"
            f"**To do this, use the following method:**\n{example_blocks}"
        )
    else:
        log.trace("Aborting missing language instructions: content is not Python code.")


def get_instructions(content: str) -> Optional[str]:
    """Return code block formatting instructions for `content` or None if nothing's wrong."""
    log.trace("Getting formatting instructions.")

    blocks = parsing.find_code_blocks(content)
    if blocks is None:
        log.trace("At least one valid code block found; no instructions to return.")
        return

    if not blocks:
        log.trace(f"No code blocks were found in message.")
        return _get_no_ticks_message(content)
    else:
        log.trace("Searching results for a code block with invalid ticks.")
        block = next((block for block in blocks if block.tick != parsing.BACKTICK), None)

        if block:
            log.trace(f"A code block exists but has invalid ticks.")
            return _get_bad_ticks_message(block)
        else:
            log.trace(f"A code block exists but is missing a language.")
            block = blocks[0]

            # Check for a bad language first to avoid parsing content into an AST.
            description = _get_bad_lang_message(block.content)
            if not description:
                description = _get_no_lang_message(block.content)

            return description
