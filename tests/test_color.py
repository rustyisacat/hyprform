from hyprform import color


def test_single_color_round_trips_in_original_style():
    cases = [
        "rgba(33ccffee)",
        "rgb(33ccff)",
        "0xee1a1a1a",
        "#33ccff",
        "#33ccffee",
    ]
    for raw in cases:
        parsed = color.parse_color(raw)
        assert parsed is not None, f"failed to parse {raw!r}"
        assert color.format_color(parsed.r, parsed.g, parsed.b, parsed.a, parsed.style) == raw


def test_gradient_is_not_a_single_color():
    assert color.parse_color("rgba(33ccffee) rgba(00ff99ee) 45deg") is None


def test_garbage_is_not_a_color():
    assert color.parse_color("not a color") is None
    assert color.parse_color("") is None


def test_0x_style_puts_alpha_first():
    parsed = color.parse_color("0xee1a1a1a")
    assert parsed is not None
    assert round(parsed.a * 255) == 0xEE
    assert round(parsed.r * 255) == 0x1A
