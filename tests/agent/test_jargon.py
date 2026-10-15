"""The system's own words, which a business owner is never told (`jargon`).

No model and no log: the list, read over sentences and over a kept
conversation the way the ecosystem test reads one.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.agent import jargon  # noqa: E402


def test_the_systems_words_are_found_in_english_and_in_indonesian():
    # The two-round test's first question to Sari, as the agent asked it.
    asked = ("Halo Bu Sari! Apakah yang kita buat di @kemahceria/sewa ini ditujukan "
             "khusus untuk usaha Kemah Ceria saja, atau sebagai modul umum?")
    assert jargon.found(asked) == ["@kemahceria/sewa", "modul"]
    assert jargon.found("Sudah siap disegel sebagai v2.") == ["disegel"]
    assert jargon.found("It is ready to be sealed; it pins Rudi's module.") == \
        ["sealed", "pins", "module"]
    # A name as the system writes it, composed or not, and anything in backticks.
    assert jargon.found("The rental_note on rudi_penyewaan__Rental, see `revise`.") == \
        ["rental_note", "rudi_penyewaan__Rental", "`revise`"]
    # Each word once, however often it comes.
    assert jargon.found("module, Module, modules") == ["module", "modules"]


def test_everyday_words_of_a_business_are_not_on_the_list():
    for said in ("Tenda 4 orang: 3 disewa, 1 di gudang.",
                 "The draft keeps what I did; ask me to go on.",
                 "Your rentals, from Rudi's Equipment Rental, version 2.",
                 "Jaminan Citra Rp500.000, per 12 Oktober."):
        assert jargon.found(said) == [], said


def test_a_word_the_person_used_first_is_theirs():
    assert jargon.found("The module is ready.", ["I want a module for rentals."]) == []
    assert jargon.found("Modulnya siap disegel.", ["bikin modul ya"]) == ["disegel"]


def test_every_sentence_of_an_ending_is_read_and_a_conversation_turn_by_turn():
    plan = {"message": "Is this it?", "builds": "A table per item.",
            "records": ["Your rentals (@rudi/penyewaan)."], "reuses": ["a community module"],
            "elsewhere": [], "numbers": ["Units out per item."], "cannot": []}
    assert jargon.found("\n".join(jargon.spoken(plan))) == ["@rudi/penyewaan", "module"]
    question = {"question": "For you alone?", "choices": ["Yes", "A shared module"]}
    assert jargon.spoken(question) == ["For you alone?", "Yes", "A shared module"]

    turns = [
        {"person": "Saya Sari, pemilik Kemah Ceria.",
         "said": {"question": "Untuk Kemah Ceria saja, atau modul umum?"}},
        {"person": "Untuk Kemah Ceria saja.",
         "said": {"message": "Ini rencananya: tabel alat per jenis."}},
        {"person": "Setuju, lanjut. Modulnya boleh.",
         "said": {"message": "Modul sudah siap dibekukan."}},
    ]
    # The third turn's "Modul" is the person's own word by then.
    assert jargon.leaks(turns) == [(1, ["modul"])]


def test_the_terminal_reads_kept_conversations_for_the_systems_words(tmp_path, capsys):
    import yaml

    from components.agent.__main__ import main
    kept = tmp_path / "v1.chat.yaml"
    kept.write_text(yaml.safe_dump({"turns": [
        {"person": "Halo.", "said": {"message": "Siap disegel."}},
        {"person": "Oke.", "said": {"message": "Sudah dibekukan sebagai v1."}},
    ]}), encoding="utf-8")
    assert main(["words", str(kept)]) == 1
    printed = capsys.readouterr().out
    assert "2 turns, 1 in the system's words" in printed
    assert "  turn 1: disegel" in printed
