from concurrent.futures import ThreadPoolExecutor
from tools.grade_tool import retrieval_grader

CORRECTION_THRESHOLD = 0.5  # trigger correction only if majority of chunks fail


def grade_documents(state):
    question = state["question"]
    documents = state["documents"]
    grader = retrieval_grader()

    def grade_one(doc):
        score = grader.invoke({"question": question, "document": doc.page_content})
        return doc, score["score"] == "yes"

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(grade_one, documents))

    filtered_docs = [doc for doc, passed in results if passed]
    failed = sum(1 for _, passed in results if not passed)

    web_search = "Yes" if len(documents) > 0 and (failed / len(documents)) > CORRECTION_THRESHOLD else "No"
    return {"documents": filtered_docs, "question": question, "web_search": web_search}
