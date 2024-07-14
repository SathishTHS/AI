from langchain.text_splitter import RecursiveCharacterTextSplitter

class splitter():
    chunk_size = 600
    chunk_overlap = 150
    separators = ['\n\n', '\n', '. ', ' ']
    rec_text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                                        chunk_overlap=chunk_overlap,
                                                        separators=separators)