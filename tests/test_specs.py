from pipeline import specs


def test_safe_rect_matches_meta_pixel_guidance():
    # Meta: top 14% (269 px), bottom 35% (672 px), sides 6% (65 px) on 1080x1920.
    assert specs.safe_rect() == specs.Rect(65, 269, 1015, 1248)


def test_button_column_sits_inside_the_right_edge_of_the_safe_area():
    safe, buttons = specs.safe_rect(), specs.button_column_rect()
    assert safe.contains(buttons)
    assert buttons == specs.Rect(886, 902, 1015, 1248)


def test_rect_contains_and_overlaps():
    safe = specs.safe_rect()
    centred_face = specs.Rect(390, 700, 690, 1000)
    assert safe.contains(centred_face)
    assert not safe.contains(specs.Rect(390, 100, 690, 400))  # under the username bar
    assert centred_face.overlaps(safe)
    assert not centred_face.overlaps(specs.button_column_rect())


def test_frames_and_loop_rule():
    assert specs.seconds_to_frames(8) == 240
    assert specs.seconds_to_frames(0.1) == 3
    assert specs.seconds_to_frames(1 / 60) == 1  # rounds half up, not to even
    assert specs.frame_at(0) == 1
    assert specs.frame_at(1.0) == 31
    assert specs.loop_end_frame(45) == 44


def test_jelly_hop_table_is_a_clean_loop():
    frames = [key.frame for key in specs.JELLY_HOP]
    assert frames == sorted(frames) and len(set(frames)) == len(frames)
    first, last = specs.JELLY_HOP[0], specs.JELLY_HOP[-1]
    assert (first.loc_z, first.scale_xy, first.scale_z) == (last.loc_z, last.scale_xy, last.scale_z)
    assert specs.loop_end_frame(last.frame) == 44  # guide §11.4: End = 44
    contacts = {key.frame for key in specs.JELLY_HOP if key.loc_z == 0}
    assert set(specs.JELLY_HOP_VECTOR_FRAMES) <= contacts


def test_jelly_hop_blink_fits_in_the_hold_and_follows_timing_rules():
    settle = next(k.frame for k in specs.JELLY_HOP if k.pose == "settle")
    blink_frames = [frame for frame, _ in specs.JELLY_HOP_BLINK]
    assert settle < blink_frames[0] and blink_frames[-1] < specs.JELLY_HOP[-1].frame
    duration = blink_frames[-1] - blink_frames[0]
    assert specs.BLINK_FRAMES[0] <= duration + 1 <= specs.BLINK_FRAMES[1] + 1


def test_text_hold_seconds():
    assert specs.text_hold_seconds(2) == 1.0
    assert specs.text_hold_seconds(9) == 3.0


def test_platform_limits():
    assert specs.MAX_HASHTAGS == 5
    assert (specs.WIDTH, specs.HEIGHT, specs.FPS) == (1080, 1920, 30)
    assert specs.LOUDNESS_LUFS == -14.0 and specs.TRUE_PEAK_DBTP == -1.0
    assert specs.MIN_HOLD_FRAMES == 15
