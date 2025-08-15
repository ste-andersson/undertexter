from typing import List, Dict

PUNCT = set(list(".,;:!?…"))

def segment_words(words: List[Dict], max_chars=38, max_words=9, max_dur=2.5, min_dur=0.8, gap_merge=0.08, punct_bonus=0.2):
    """
    words: list of {"w": str, "s": float, "e": float}
    returns list of cues: {"start": float, "end": float, "text": str}
    """
    cues = []
    if not words: 
        return cues
    i = 0
    n = len(words)
    while i < n:
        start = words[i]["s"]
        end = words[i]["e"]
        cue_words = [words[i]["w"]]
        text = words[i]["w"]
        j = i + 1
        while j < n:
            gap = words[j]["s"] - end
            if 0 < gap <= gap_merge:
                pass
            proposed_end = words[j]["e"]
            duration = proposed_end - start
            proposed_text = (text + " " + words[j]["w"]).strip()
            if len(proposed_text) > max_chars or len(cue_words) + 1 > max_words or duration > max_dur:
                if text and text[-1] in PUNCT and (duration - max_dur) <= punct_bonus:
                    text = proposed_text
                    cue_words.append(words[j]["w"])
                    end = proposed_end
                    j += 1
                break
            else:
                text = proposed_text
                cue_words.append(words[j]["w"])
                end = proposed_end
                j += 1
        if end - start < min_dur:
            k = j
            while (k < n) and (words[k]["s"] - end <= gap_merge) and (len(text + " " + words[k]['w']) <= max_chars + 5) and (k - i + 1 <= max_words + 1):
                text = (text + " " + words[k]["w"]).strip()
                end = words[k]["e"]
                k += 1
            j = max(j, k)
        cues.append({"start": start, "end": end, "text": text})
        i = j if j > i else i + 1
    return cues
