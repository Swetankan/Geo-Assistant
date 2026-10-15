import re
from app.schemas import Answer, Citation

ABSTENTION='I cannot answer this from the available sources'


def safety_reason(query):
    if re.search(r'\b(delete|drop|truncate|overwrite|modify|update|insert|erase|remove)\b.{0,45}\b(data|index|records?|school|database|layer|files?)\b',query,re.I):
        return 'Data mutation is not supported'
    if re.search(r'\b(system prompt|api.?key|password|credentials?|secrets?)\b',query,re.I):
        return 'Secret or system instruction disclosure is not supported'
    if re.search(r'ignore.{0,30}(instructions|rules)|system\s*:|developer\s*:|reveal.{0,20}prompt',query,re.I):
        return 'Instruction override request'
    return None


def suspicious_passage(text):
    return bool(re.search(r'ignore.{0,40}(instructions|rules)|system\s*:|developer\s*:|reveal.{0,30}(secret|prompt)|send.{0,30}(password|api.key)',text,re.I))


def citation_for(chunk):
    return Citation(chunk_id=chunk.id,source=chunk.source,page=chunk.page,start=chunk.start,end=chunk.end,excerpt=chunk.text)


def validate_citations(answer: Answer,retrieved):
    """Checks provenance only, NOT semantic support for claims."""
    for citation in answer.citations:
        chunk=retrieved.get(citation.chunk_id)
        if chunk is None:
            raise ValueError('Citation references unretrieved chunk')
        if citation != citation_for(chunk):
            raise ValueError('Citation metadata/excerpt differs from retrieved source')
    if answer.answer != ABSTENTION and not answer.citations:
        raise ValueError('Non-abstaining answer requires citations')


def redact(text):
    text=re.sub(r'(?i)(authorization\s*[:=]\s*)(?:basic|bearer|apikey)\s+\S+',r'\1[REDACTED]',text)
    text=re.sub(r'(?i)((?:password|api[_-]?key|secret|token)\s*[:=]\s*)[^\s,;]+',r'\1[REDACTED]',text)
    return re.sub(r'(https?://)[^/@\s]+:[^/@\s]+@',r'\1[REDACTED]@',text)
