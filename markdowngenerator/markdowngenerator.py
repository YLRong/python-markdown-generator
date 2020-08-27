import tempfile
from pathlib import Path
import logging

linesep = '\n'
from typing import List
from html import escape
from string import punctuation
from .syntax import (
    MARKDOWN_HEADER as HEADER,
    HTML_SPACE,
    MARKDOWN_HORIZONTAL_RULE as HORIZONTAL_RULE,
    MARKDOWN_SINGLE_LINE_BLOCKQUOTE as SINGLE_LINE_BLOCKQUOTE,
    MARKDOWN_MULTILINE_BLOCKQUOTE as MULTILINE_BLOCKQUOTE,
    MARKDOWN_CODE_BLOCK as CODE_BLOCK,
    MARKDOWN_INLINE_CODE_HL as INLINE_CODE_HIGHLIGHT,
    FOOTNOTE_IDENTIFIER,
)
from .conf import (
    DEFAULT_FILE_LOCATION,
    MAX_HEADER_LEVEL,
    MIN_HEADER_LEVEL,
    TABLE_OF_CONTENT_LINE_POSITION,
)

# from standardizer.markdown.config.log import logger


class MarkdownGenerator:
    """Class for generating GitLab or GitHub flavored Markdown."""

    """
    Instance of this class or any subclass is excepted to initialize
    by using 'with' statement in most cases.

    This opens file where content should be written.
    Default filename is default_file.md
    """

    def __init__(
        self,
        _self=None,
        document=None,
        filename=None,
        description=None,
        syntax=None,
        root_object=True,
        tmp_dir=None,
        pending_footnote_references=None,
        footnote_index=None,
        header_data_array=None,
        header_index=None,
        document_data_array=None,
        enable_write=False,
        enable_TOC=True,
        logger=None,
    ):
        """
        Constructor method for MarkdownGenerator

        GitLab allows following HTML tags as well:
        https://www.rubydoc.info/gems/html-pipeline/1.11.0/HTML/Pipeline/SanitizationFilter#WHITELIST-constant

        :param document: existing opened document file, defaults to None
        :param filename: File to be opened, defaults to None
        :param description: Description of generated document, defaults to None
        :param syntax: Markdown syntax flavor (GitHub vs GitLab)
        :param root_object: Whether the instance of this class is root object, defaults to None
        :param tmp_dir: Path of temporal directory. NOTE: not in user, defaults to None
        :param pending_footnote_references, defaults to None
        :param footnote_index
        """

        self.logger = logger if logger else logging.getLogger()
        self.logger.name = __name__
        self.logger.debug("Filename in constructor is {}".format(filename))

        # Attribute for determining if object is first instance of Markdowngenerator
        # It has has file open, which should be noted on exit.
        self.root_object = root_object

        self.description = "Class for generating GitLab flavored Markdown."

        self.document = document
        """
        Attribute for storing everything what is written into the file.
        Makes the manipulation of data in the middle of documenting easier,
        without re-reading and rewriting the document again if defined that
        data will be written only in the end of execution.

        NOTE: This variable should be shared and passed into every child node
        in constructor, that document structure keeps in correct.

        One index in array is one line in file.
        """
        self.document_data_array = document_data_array if document_data_array else []
        self.enable_write = enable_write
        self.enable_TOC = enable_TOC
        ###########
        if not filename:
            self.logger.info(
                "No file location given. Using default '{}'."
                " Overwriting existing file.".format(DEFAULT_FILE_LOCATION)
            )
            self.filename = Path(DEFAULT_FILE_LOCATION).resolve()
            self.default_filename_on_use = True
        elif isinstance(filename, Path):
            self.filename = filename
            self.default_filename_on_use = False
        else:
            self.filename = Path(filename).resolve()
            self.default_filename_on_use = False
        self.syntax = syntax if syntax else "gitlab"

        # Index for amount of footnotes and list of actual notes
        # to be written into the end of file
        # We are using dict, so we can pass it by reference among objects
        self.footnote_index = footnote_index if footnote_index else {"value": 0}
        self.pending_footnote_references = (
            pending_footnote_references if pending_footnote_references else []
        )

        # Trailing details, details section open but not ended if count > 0.
        self.unfinished_details_summary_count = {"value": 0}

        # Header information for table of contents
        self.header_info = header_data_array if header_data_array else []
        self.header_index = header_index if header_index else 0

        # Directory for tmp files, currently not in use.
        self.tmp_dir = tmp_dir

    def __enter__(self):
        """
        Override default enter method to enable
        usage of 'with' while using class instance
        to safely open and close file.

        """

        if self.filename.is_dir():
            self.filename.mkdir(exist_ok=True)
            self.logger.debug(
                "Given path is directory without filename, using default filename."
            )
            self.filename.joinpath(DEFAULT_FILE_LOCATION, ".md")
            self.default_filename_on_use = True
        if not self.document:
            self.document = open(f"{self.filename}", "w+")
            current_tmp_dir = tempfile.gettempdir()
            self.tmp_dir = tempfile.TemporaryDirectory(dir=current_tmp_dir)

        # self.filename = os.path.basename(self.filename)
        return self

    def __exit__(self, *args, **kwargs):
        """
        Close file on exit.

        If there are some footnotes to be written, write them first.
        If Table of Contents should be written, it will be.

        If we have just generated the content of file into the memory,
        now write all at once into the file.

        """

        # Everything will be written at once into the file
        if not self.enable_write:
            self.document.writelines(self.document_data_array)
        self.document.close()

    def writeText(self, text, html_escape: bool = True):
        """
        Method for writing arbitrary text into the document file,
        or just adding data into document data structure for easier manipulation.

        Text input has been escaped by default from HTML characters which could mess up the document..

        :param text: Input text string
        :param html_escape: bool,  Whether the input should be escaped or not
        """
        if html_escape:
            self.document_data_array.append(escape(str(text)))
            if self.enable_write:
                self.document.write(escape(str(text)))
            return
        self.document_data_array.append(str(text))
        if self.enable_write:
            self.document.write(str(text))

    def writeTextLine(self, text=None, html_escape: bool = True):
        """
        Write arbitrary text into the document file and add new line,
        or just adding data with new line into document data structure for easier manipulation.

        Writing is defined in attribute 'self.enable_write' whether it is true or false

        Note double spaces after text.

        Text input has been escaped by default from HTML characters which could mess up the document..

        :param text: Input text string
        :param html_escape: bool, Whether the input should be escaped or not
        """
        if text is None:
            # Just forcing new line, in Markdown there should be 2 or more spaces as well
            self.document_data_array.append(str("  ") + linesep)
            if self.enable_write:
                self.document.write(str("  ") + linesep)

            return
        if html_escape:
            self.document_data_array.append(escape(str(text)) + "  " + linesep)
            if self.enable_write:
                self.document.write(escape(str(text)) + "  " + linesep)
            return
        self.document_data_array.append(str(text) + "  " + linesep)
        if self.enable_write:
            self.document.write(str(text) + "  " + linesep)

    """
    Emphasis, aka italics, bold or strikethrough.
    """

    def addBoldedText(self, text: str, write_as_line: bool = False) -> str:
        """
        Standard Markdown

        Method for bolding text
        See: https://docs.gitlab.com/ee/user/markdown.html#emphasis
        Removes leading and trailing whitespaces.

        :param text: Input text to be bolded.
        :param write_as_line: bool, Whether the text should be written to document/buffer directly
        :return: str, Bolded text
        :rtype: string
        """
        bolded = f"**{text.strip()}**"
        if write_as_line:
            self.writeTextLine(bolded)
        return bolded

    def addItalicizedText(self, text, write_as_line: bool = False) -> str:
        """
        Standard Markdown

        Method for italicizing text
        See: https://docs.gitlab.com/ee/user/markdown.html#emphasis
        Removes leading and trailing whitespaces.

        :param text: Input text to be italicized
        :param write_as_line: bool, Whether the text should be written to document/buffer directly
        :return: Italicized text
        :rtype: string
        """
        italicized = f"*{text.strip()}*"
        if write_as_line:
            self.writeTextLine(italicized)
        return italicized

    def addBoldedAndItalicizedText(self, text, write_as_line: bool = False) -> str:
        """
        Standard Markdown

        Method for bolding and italicing text
        See: https://docs.gitlab.com/ee/user/markdown.html#emphasis
        Removes leading and trailing whitespaces.

        :param text: Input text to be italicized and boldgin.
        :param write_as_line: bool, Whether the text should be written to document/buffer directly
        :return: Bolded text
        :rtype: string
        """
        bolded_italicized = f"***{text.strip()}***"
        if write_as_line:
            self.writeTextLine(bolded_italicized)
        return bolded_italicized

    def generateHrefNotation(self, text, url, title=None) -> str:
        """
        Standard Markdown

        Method for generating link into markdown document.
        See: https://docs.gitlab.com/ee/user/markdown.html#links

        :param text: Visible text
        :param text: URL of the wanted destination
        :param title: Title for URL. Tooltip on hover
        :return: formated markdown reprenstation text
        :rtype: string
        """
        if title:
            return f'[{text}]({url} "{title}")'
        return f"[{text}]({url})"

    def generateImageHrefNotation(self, image_uri: str, alt_text, title=None) -> str:
        """
        Standard Markdown

        Method for showing image in Markdown.

        GitLab supports videos and audio as well, and is able to play video, if extension is valid as
        described in here: https://docs.gitlab.com/ee/user/markdown.html#videos

        :param image_path: Path or URL into the image
        :param alt_text: Text which appears if image not loaded
        :param title: Title for the image
        :return: Formatted presentation of image in Markdown
        :rtype: string
        """

        if title:
            return f'![{alt_text}]({image_uri} "{title}")'
        return f"![{alt_text}]({image_uri})"

    def addHorizontalRule(self):
        """
        Standard Markdown

        Method for appending Horizontal Rule:
        See: https://docs.gitlab.com/ee/user/markdown.html#horizontal-rule
        """
        self.writeTextLine(f"{linesep}{HORIZONTAL_RULE}{linesep}")

    def addCodeBlock(self, text, syntax: str = None, escape_html: bool = False):
        """
        Standard Markdown

        Method for inserting highlighted code block into the Markdown file
        See: https://docs.gitlab.com/ee/user/markdown.html#code-and-syntax-highlighting

        :param text: Actual content/code into code block
        :param syntax: string, Syntax highlight type for code block
        :param escape_html: bool, Wheather the input is html escaped or not
        """

        # Escape backtics/grave accents in attempt to deny codeblock escape
        grave_accent_escape = "\`"

        text = text.replace("`", grave_accent_escape)

        if escape_html:
            self.writeTextLine(
                f"{CODE_BLOCK}{syntax}{linesep}{text}{linesep}{CODE_BLOCK}"
            )
        else:
            self.writeTextLine(
                f"{CODE_BLOCK}{syntax}{linesep}{text}{linesep}{CODE_BLOCK}",
                html_escape=False,
            )

    def addInlineCodeBlock(self, text, escape_html: bool = False, write: bool = False):
        """
        Standard Markdown

        Method for adding highlighted code in inline style in Markdown.
        By default in Markdown, it is done by using single backticks: `

        :param text: Actual content/code into code block
        :param escape_html: Wheather the input is html escaped or not. Default is True
        :param write: Wheather the output is written immediately or returned. 
        :return: If write is false, generated InlineCodeBlock is returned
        :rtype: string
        By default constructed output is returned only.
        """

        inline_hl = f"{INLINE_CODE_HIGHLIGHT}{text}{INLINE_CODE_HIGHLIGHT}"
        if write:
            if escape_html:
                self.writeText(inline_hl)
            else:
                self.writeText(inline_hl, html_escape=False)
        else:
            return inline_hl

    def addSinglelineBlockQuote(self, text):
        """
        Standard Markdown

        Method for adding single line blockquote.
        Removes leading or trailing whitespaces from input.

        Escape input already here to enable ">" default blockquote character.

        :param text: Input to be written as single line blockquote
        """
        self.writeTextLine(
            f"{SINGLE_LINE_BLOCKQUOTE}{escape(text.strip())}", html_escape=False
        )

    def addMultiLineBlockQuote(self, text):
        """
        NOTE: GitLab Markdown Only

        Method for adding multiline blockquote.
        See: https://docs.gitlab.com/ee/user/markdown.html#multiline-blockquote
        Removes leading or trailing whitespaces from input.

        Escape input already here to enable ">" default blockquote character.

        :param text: Input text for inside blockquote
        """
        self.writeTextLine(
            f"{MULTILINE_BLOCKQUOTE}{linesep}{escape(text.strip())}{linesep}{MULTILINE_BLOCKQUOTE}",
            html_escape=False,
        )

    def addTable(
        self,
        header_names: List[str] = None,
        row_elements=None,
        alignment="center",
        dictionary_list=None,
        html_escape=True,
        capitalize_headers=False,
    ):
        """
        Standard Markdown

        Method for generating Markdown table with centered cells.

        If both row_elements and dictionary_list is provided, dictionary_list is used by default.

        If only dictionary_list paramater is provided, function expects that it has list of same type dictionaries.
        Key names of dictionary will be used as header names for table.

        :param header_names: List of header names, defines width of table
        :param row_elements: List of lists. (List of rows, each row contains list of row's elements)
        :param dictionary_list: List of dictionary. Expecting only attributes inside dictionary, no nested objects.
        :param alignment: Alignment of all columns in table
        """
        useDictionaryList = False
        useProvidedHeadernames = False

        if row_elements is None:
            if dictionary_list is None:
                self.logger.warning("Invalid paramaters for generating new table.")
                raise TypeError(
                    f"Invalid paramaters for generating new table. Use either dictionary list or row_elements."
                )
            else:
                useDictionaryList = True

        if row_elements and dictionary_list:
            self.logger.debug(
                "Both row elements and dictionary list provided, using dictionary list as default."
            )

        if header_names:
            self.logger.debug("Header names provided. Using them.")
            useProvidedHeadernames = True
        else:
            self.logger.debug(
                "No header names provided. Using dictionary attribute names as default. Using none, if row_elements used."
            )

        # Headers
        self.writeTextLine()
        if not useProvidedHeadernames and dictionary_list:
            try:
                header_names = dictionary_list[0].keys()
                self.logger.debug(f"Header names are: {header_names}")
            except AttributeError as e:
                self.logger.error(
                    f"Dictionary list for addTable function was not list of objects. Table not generated. : {e}"
                )
                return
        try:
            for header in header_names:
                # Capitalize header names
                if capitalize_headers:
                    self.writeText(f"| {header.capitalize()} ")
                else:
                    self.writeText(f"| {header} ")
        except TypeError as e:
            self.logger.error(f"Invalid header names for table. Not generated: {e}")
            return
        # Write ending vertical bar
        self.writeTextLine(f"|")

        # Write dashes to separate headers
        if alignment == "left":
            self.writeTextLine("".join(["|", ":---|" * len(header_names)]))

        elif alignment == "center":
            self.writeTextLine("".join(["|", ":---:|" * len(header_names)]))
            # self.__exit__()
            # exit()

        elif alignment == "right":
            self.writeTextLine("".join(["|", "---:|" * len(header_names)]))
        else:
            self.logger.warning("Invalid alignment value in addTable. Using default.")
            self.writeTextLine("".join(["|", ":---:|" * len(header_names)]))

        # Write each row into the table
        if not useDictionaryList:

            for row in row_elements:
                if len(row) > len(header_names):
                    self.logger.error(
                        f"The are more row elements than header names (Row: {len(row)} - Header: {len(header_names)} "
                    )
                    continue
                for element in row:
                    # Check if element is list
                    # If it is, add it as by line by line into single cell
                    if isinstance(element, list):
                        self.writeText("| ")
                        for list_str in element:
                            self.writeText(list_str)
                            self.writeText("<br> ", html_escape=False)
                    else:
                        self.writeText(f"| {element} ", html_escape)

                self.writeTextLine(f"|")

        else:
            # Iterate over list of dictionaries
            # One row contains attributes of dictionary
            for row in dictionary_list:
                for key in row.keys():
                    if isinstance(row.get(key), list):
                        self.writeText("| ")
                        for list_str in row.get(key):
                            self.writeText(list_str)
                            self.writeText("<br> ", html_escape=False)
                    else:
                        self.writeText(f"| {row.get(key)} ", html_escape)
                self.writeTextLine(f"|")
        self.writeTextLine()