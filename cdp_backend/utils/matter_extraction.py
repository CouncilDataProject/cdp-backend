import textract


def get_matter_text(uri: str) -> str:
    """
    Get the text contained in a particular docx, ppt, pdf, other text file.

    Parameters
    ----------
    uri: str
        The text file's uri.

    Returns
    -------
    matter_text: str
        The text contained within the text file.
    """
    text = textract.process(uri)
    return text
