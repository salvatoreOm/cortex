import pytest

from app.utils.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_a_single_chunk():
    text = "one two three"
    assert chunk_text(text, chunk_size=500, overlap=50) == [text]


def test_splits_into_overlapping_chunks():
    words = [f"w{i}" for i in range(120)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=50, overlap=10)

    assert len(chunks) == 3
    assert chunks[0] == " ".join(words[0:50])
    assert chunks[1] == " ".join(words[40:90])
    assert chunks[2] == " ".join(words[80:120])


def test_overlap_words_appear_in_both_neighboring_chunks():
    words = [f"w{i}" for i in range(20)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=10, overlap=4)

    first_words = chunks[0].split()
    second_words = chunks[1].split()
    assert first_words[-4:] == second_words[:4]


def test_rejects_invalid_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=0)


def test_rejects_overlap_not_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=10, overlap=10)
