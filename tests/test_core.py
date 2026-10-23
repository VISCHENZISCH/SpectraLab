from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from spectralab.core import image_ops, metadata
from spectralab.core.activity import ActivityLog
from spectralab.core.paths import derived_path, unique_path
from spectralab.core.tools import find_tool

needs_exiftool = pytest.mark.skipif(find_tool("exiftool") is None, reason="ExifTool absent")


@pytest.fixture
def photo(tmp_path: Path) -> Path:
    path = tmp_path / "photo é.jpg"
    exif = Image.Exif()
    exif[0x010F] = "Canon"  # Make
    exif[0x013B] = "Jane Doe"  # Artist
    exif[0x0112] = 6  # Orientation : rotation 90°
    Image.new("RGB", (40, 20), "red").save(path, exif=exif)
    return path


def test_unique_path_never_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "a.txt"
    assert unique_path(target) == target
    target.write_text("x")
    assert unique_path(target).name == "a (2).txt"
    assert derived_path(target, "_clean").name == "a_clean.txt"


@pytest.mark.parametrize("tag", ["Artist", "XMP-dc:Creator", "GPSLatitude"])
def test_valid_tags(tag: str) -> None:
    assert metadata.validate_tag(tag) == tag


@pytest.mark.parametrize("tag", ["", "-all", "Artist<", "Comment+", "a b", "TagsFromFile=@", "Artist-"])
def test_invalid_tags_rejected(tag: str) -> None:
    with pytest.raises(ValueError):
        metadata.validate_tag(tag)


def test_privacy_findings_ignore_filesystem_groups() -> None:
    entries = [
        metadata.Entry("GPS", "GPSLatitude", "48.85"),
        metadata.Entry("IFD0", "Make", "Canon"),
        metadata.Entry("ExifIFD", "BodySerialNumber", "123"),
        metadata.Entry("System", "FileName", "a.jpg"),
        metadata.Entry("Composite", "GPSPosition", "48.85, 2.35"),
    ]
    findings = metadata.privacy_findings(entries)
    assert [f.label for f in findings] == ["Numéro de série d'appareil", "Position GPS", "Appareil et logiciel"]
    assert metadata.risk_level(findings) is metadata.Severity.HIGH


@needs_exiftool
def test_read_and_clean_copy(photo: Path) -> None:
    [meta] = metadata.read_metadata([photo])
    assert meta.error is None
    tags = {e.tag: e.value for e in meta.embedded}
    assert tags["Make"] == "Canon" and tags["Artist"] == "Jane Doe"

    cleaned = metadata.clean_copy(photo)
    assert cleaned.name == "photo é_clean.jpg"
    [after] = metadata.read_metadata([cleaned])
    remaining = {e.tag for e in after.embedded}
    assert "Make" not in remaining and "Artist" not in remaining
    assert "Orientation" in remaining  # conservée : rendu identique
    assert photo.exists()  # l'original n'est pas touché


@needs_exiftool
def test_write_tags_value_is_never_an_option(photo: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.jpg"
    metadata.write_tags(photo, {"Artist": "-all= -o /tmp/x", "XMP-dc:Rights": "© Studio"}, output=out)
    tags = {e.tag: e.value for e in metadata.read_metadata([out])[0].embedded}
    assert tags["Artist"] == "-all= -o /tmp/x"
    assert tags["Rights"] == "© Studio"


@needs_exiftool
def test_newlines_rejected(photo: Path) -> None:
    with pytest.raises(ValueError):
        metadata.write_tags(photo, {"Artist": "a\n-all="})


def test_convert_and_resize(photo: Path) -> None:
    converted = image_ops.convert_image(photo, "PNG")
    assert converted.path.suffix == ".png"
    assert converted.dimensions == (20, 40)  # orientation EXIF appliquée
    with Image.open(converted.path) as img:
        assert not img.getexif()  # métadonnées non recopiées par défaut

    resized = image_ops.resize_image(photo, 10)
    assert resized.dimensions == (10, 20)
    assert resized.path.name == "photo é_10x20.jpg"

    with pytest.raises(ValueError):
        image_ops.resize_image(photo, 0)


def test_activity_log_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "activity.json"
    log = ActivityLog(path)
    day = date(2026, 10, 23)
    log.record("analysis", 3, today=day)
    log.record("clean", today=day)
    reloaded = ActivityLog(path)
    assert reloaded.total("analysis", today=day) == 3
    assert reloaded.last_days(7, today=day)[-1] == (day, {"analysis": 3, "clean": 1})
    with pytest.raises(ValueError):
        log.record("unknown")


def test_activity_log_ignores_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "activity.json"
    path.write_text('{"not-a-date": {"analysis": 1}, "2026-10-01": {"analysis": -5, "evil": 3}}')
    assert ActivityLog(path).last_days(1, today=date(2026, 10, 1))[0][1] == {}
