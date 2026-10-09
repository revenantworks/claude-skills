"""Tests for obs_ws.py, obs_audit.py and obs_post.py.

Run: python -m unittest discover -s scripts -p "test_*.py"   (from the skill folder)

No OBS, no FFmpeg, no GPU and no obsws-python package are needed. The websocket client is an
injected fake; FFmpeg and FFprobe are fake Python scripts written to a temp folder at runtime and
steered by environment variables (FAKE_PIX, FAKE_DUR). The localops state dir (the GPU lease) is a
temp folder set through LOCALAPPDATA and XDG_STATE_HOME, so the user's real lease is never touched.
"""
import configparser
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import obs_audit  # noqa: E402
import obs_post  # noqa: E402
import obs_ws  # noqa: E402

FAKE_FFMPEG = r'''
import json, os, sys
args = sys.argv[1:]
if os.environ.get("FAKE_FFMPEG_FAIL") == "1":
    sys.exit(1)
joined = " ".join(args)
if "print_format=json" in joined:
    sys.stderr.write('[Parsed_loudnorm_0]\n{\n "input_i" : "-23.10",\n "input_tp" : "-4.20",\n'
                     ' "input_lra" : "6.30",\n "input_thresh" : "-33.40",\n "target_offset" : "0.10"\n}\n')
    sys.exit(0)
out = args[-1]
if "%03d" in out:
    out = out.replace("%03d", "001")
with open(out, "wb") as f:
    f.write(("fake render " + joined).encode("utf-8"))
log = os.environ.get("FAKE_FFMPEG_LOG")
if log:
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(args) + "\n")
'''

FAKE_FFPROBE = r'''
import json, os, sys
print(json.dumps({
    "streams": [
        {"codec_type": "video", "codec_name": os.environ.get("FAKE_VCODEC", "h264"),
         "pix_fmt": os.environ.get("FAKE_PIX", "yuv420p"), "avg_frame_rate": "30/1",
         "width": 1920, "height": 1080},
        {"codec_type": "audio", "codec_name": os.environ.get("FAKE_ACODEC", "aac")}],
    "format": {"duration": os.environ.get("FAKE_DUR", "10.0")}}))
'''


class FakeClient:
    def __init__(self, log, responses=None):
        self.log = log
        self.responses = responses or {}

    def send(self, request, data=None, raw=False):
        self.log.append((request, data))
        return self.responses.get(request, {"ok": True})


def factory_with(log, responses=None):
    made = []

    def factory(host, port, password, timeout):
        made.append((host, port))
        return FakeClient(log, responses)
    factory.made = made
    return factory


class StateDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._env = {k: os.environ.get(k) for k in ("LOCALAPPDATA", "XDG_STATE_HOME", "OBS_WEBSOCKET_PASSWORD")}
        os.environ["LOCALAPPDATA"] = str(self.root / "state")
        os.environ["XDG_STATE_HOME"] = str(self.root / "state")
        (self.root / "state" / "localops").mkdir(parents=True)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def lease_path(self):
        return self.root / "state" / "localops" / "gpu-lease.json"


# ---- obs_ws: the allow-list ---------------------------------------------------------------

class AllowListTests(unittest.TestCase):
    def test_go_live_and_key_requests_are_denied(self):
        for name in ("StartStream", "StopStream", "ToggleStream", "GetStreamServiceSettings",
                     "SetStreamServiceSettings", "StartVirtualCam", "ToggleVirtualCam",
                     "TriggerHotkeyByName", "TriggerHotkeyByKeySequence", "StartOutput", "CallVendorRequest"):
            self.assertEqual(obs_ws.classify(name), "deny", name)

    def test_read_write_and_unknown_tiers(self):
        self.assertEqual(obs_ws.classify("GetStats"), "read")
        self.assertEqual(obs_ws.classify("GetRecordStatus"), "read")
        self.assertEqual(obs_ws.classify("SetCurrentProgramScene"), "write")
        self.assertEqual(obs_ws.classify("RemoveScene"), "unknown")

    def test_denied_request_never_reaches_a_client_even_with_confirm(self):
        log = []
        f = factory_with(log)
        r = obs_ws.call("StartStream", confirm=True, factory=f)
        self.assertEqual(r["status"], "REFUSED")
        self.assertEqual(f.made, [])
        r = obs_ws.call("GetStreamServiceSettings", factory=f)
        self.assertEqual(r["status"], "REFUSED")
        self.assertIn("stream key", r["reason"])
        self.assertEqual(log, [])

    def test_unknown_request_is_refused(self):
        f = factory_with([])
        self.assertEqual(obs_ws.call("RemoveInput", confirm=True, factory=f)["status"], "REFUSED")
        self.assertEqual(f.made, [])

    def test_write_needs_confirm(self):
        log = []
        f = factory_with(log)
        r = obs_ws.call("SetCurrentProgramScene", {"sceneName": "BRB"}, factory=f)
        self.assertEqual(r["status"], "REFUSED")
        self.assertEqual(log, [])
        r = obs_ws.call("SetCurrentProgramScene", {"sceneName": "BRB"}, confirm=True, factory=f)
        self.assertEqual(r["status"], "OK")
        self.assertEqual(log, [("SetCurrentProgramScene", {"sceneName": "BRB"})])

    def test_profile_parameter_only_in_the_audited_categories(self):
        # Audit O-2: SetProfileParameter may set only the categories the audit fixes.
        for cat in ("Output", "Video", "SimpleOutput", "AdvOut"):
            log = []
            data = {"parameterCategory": cat, "parameterName": "x", "parameterValue": "1"}
            r = obs_ws.call("SetProfileParameter", data, confirm=True, factory=factory_with(log))
            self.assertEqual(r["status"], "OK", cat)
            self.assertEqual(len(log), 1)
        for bad in ({"parameterCategory": "Stream1", "parameterName": "x", "parameterValue": "1"},
                    {"parameterCategory": "output", "parameterName": "x", "parameterValue": "1"},
                    {"parameterName": "x", "parameterValue": "1"}, None):
            log = []
            r = obs_ws.call("SetProfileParameter", bad, confirm=True, factory=factory_with(log))
            self.assertEqual(r["status"], "REFUSED", bad)
            self.assertIn("parameterCategory", r["reason"])
            self.assertEqual(log, [])

    def test_read_runs_without_confirm(self):
        log = []
        r = obs_ws.call("GetVersion", factory=factory_with(log, {"GetVersion": {"obsVersion": "32.2.2"}}))
        self.assertEqual(r["status"], "OK")
        self.assertEqual(r["response"]["obsVersion"], "32.2.2")

    def test_non_loopback_host_refused(self):
        f = factory_with([])
        r = obs_ws.call("GetVersion", host="192.168.1.20", factory=f)
        self.assertEqual(r["status"], "REFUSED")
        self.assertEqual(f.made, [])

    def test_missing_package_is_not_run(self):
        def factory(*a):
            raise ImportError("No module named 'obsws_python'")
        r = obs_ws.call("GetVersion", factory=factory)
        self.assertEqual(r["status"], "NOT-RUN")
        self.assertIn("install-walkthrough", r["reason"])

    def test_unreachable_names_safe_mode(self):
        def factory(*a):
            raise ConnectionRefusedError("refused")
        r = obs_ws.call("GetVersion", factory=factory)
        self.assertEqual(r["status"], "ERROR")
        self.assertIn("Safe Mode", r["reason"])

    def test_mask_hides_secrets_and_url_queries(self):
        data = {"settings": {"key": "live_abc123", "server": "rtmp://ingest.example/app"},
                "inputSettings": {"url": "https://alerts.example/widget?token=zzz999"},
                "password": "pw", "nested": [{"bearer": "tok"}]}
        dumped = json.dumps(obs_ws.mask(data))
        for secret in ("live_abc123", "zzz999", '"pw"', '"tok"'):
            self.assertNotIn(secret, dumped)
        self.assertIn("rtmp://ingest.example/app", dumped)

    def test_password_never_in_result(self):
        os.environ["OBS_WEBSOCKET_PASSWORD"] = "s3cret-pass"
        try:
            def factory(*a):
                raise ConnectionRefusedError("refused s3cret-pass")
            r = obs_ws.call("GetVersion", factory=factory)
            self.assertNotIn("s3cret-pass", json.dumps(r))
        finally:
            os.environ.pop("OBS_WEBSOCKET_PASSWORD", None)


class DiagnoseTests(unittest.TestCase):
    BASE = {"cpuUsage": 20.0, "availableDiskSpace": 500000.0, "activeFps": 60.0,
            "renderSkippedFrames": 0, "renderTotalFrames": 1000,
            "outputSkippedFrames": 0, "outputTotalFrames": 1000}

    def after(self, **kw):
        a = dict(self.BASE, renderTotalFrames=4600, outputTotalFrames=4600)
        a.update(kw)
        return a

    def test_healthy(self):
        self.assertEqual(obs_ws.diagnose(self.BASE, self.after())["bottleneck"], "none")

    def test_render_bound(self):
        d = obs_ws.diagnose(self.BASE, self.after(renderSkippedFrames=200))
        self.assertEqual(d["bottleneck"], "render")

    def test_encode_bound(self):
        d = obs_ws.diagnose(self.BASE, self.after(outputSkippedFrames=300))
        self.assertEqual(d["bottleneck"], "encode")

    def test_network_bound(self):
        d = obs_ws.diagnose(self.BASE, self.after(), {"outputActive": True, "outputCongestion": 0.6,
                                                     "outputReconnecting": False})
        self.assertEqual(d["bottleneck"], "network")

    def test_disk_low(self):
        d = obs_ws.diagnose(self.BASE, self.after(availableDiskSpace=4000.0), record_active=True)
        self.assertEqual(d["bottleneck"], "disk")


# ---- obs_audit ------------------------------------------------------------------------------

def write_profile(root: Path, adv=None, simple=None, output_mode="Advanced", stream_enc=None,
                  record_enc=None, service=None) -> Path:
    prof = root / "profile"
    prof.mkdir(parents=True, exist_ok=True)
    cp = configparser.ConfigParser()
    cp.optionxform = str
    cp["Output"] = {"Mode": output_mode}
    cp["AdvOut"] = adv or {}
    cp["SimpleOutput"] = simple or {}
    cp["Video"] = {"BaseCX": "1920", "BaseCY": "1080", "OutputCX": "1920", "OutputCY": "1080", "FPSCommon": "60"}
    with open(prof / "basic.ini", "w", encoding="utf-8-sig") as f:
        cp.write(f)
    if stream_enc is not None:
        (prof / "streamEncoder.json").write_text(json.dumps(stream_enc), encoding="utf-8")
    if record_enc is not None:
        (prof / "recordEncoder.json").write_text(json.dumps(record_enc), encoding="utf-8")
    if service is not None:
        (prof / "service.json").write_text(json.dumps(service), encoding="utf-8")
    return prof


def row(result, name):
    for r in result["rows"]:
        if r["row"] == name:
            return r
    raise AssertionError(f"no row {name!r} in {[r['row'] for r in result['rows']]}")


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def adv(self, **kw):
        a = {"Encoder": "av1_texture_amf", "RecEncoder": "h265_texture_amf", "RecFormat2": "mkv",
             "TrackIndex": "1", "VodTrackEnabled": "true", "VodTrackIndex": "2",
             "RecFilePath": str(self.root)}
        a.update(kw)
        return a

    def test_av1_on_rdna2_fails_with_fix(self):
        prof = write_profile(self.root, adv=self.adv(), stream_enc={"rate_control": "CBR", "keyint_sec": 2})
        r = row(obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 6700 XT"), "stream encoder")
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("AV1 encoder missing on this GPU", r["detail"])
        self.assertIn("HEVC or H.264 AMF", r["fix"])

    def test_av1_on_rdna3_passes(self):
        prof = write_profile(self.root, adv=self.adv(), stream_enc={"rate_control": "CBR", "keyint_sec": 2})
        r = row(obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 7900 XTX"), "stream encoder")
        self.assertEqual(r["verdict"], "PASS")

    def test_unknown_gpu_is_not_run(self):
        prof = write_profile(self.root, adv=self.adv(), stream_enc={"rate_control": "CBR", "keyint_sec": 2})
        r = row(obs_audit.audit_profile(prof, gpu_name=None), "stream encoder")
        self.assertEqual(r["verdict"], "NOT-RUN")

    def test_simple_mode_av1_also_caught(self):
        prof = write_profile(self.root, output_mode="Simple",
                             simple={"StreamEncoder": "amd_av1", "RecEncoder": "amd", "RecFormat2": "mkv",
                                     "FilePath": str(self.root)})
        r = row(obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 6700 XT"), "stream encoder")
        self.assertEqual(r["verdict"], "FAIL")

    def test_rate_control_and_keyframe(self):
        prof = write_profile(self.root, adv=self.adv(Encoder="h264_texture_amf"),
                             stream_enc={"rate_control": "VBR"})
        res = obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 6700 XT")
        self.assertEqual(row(res, "stream rate control")["verdict"], "FAIL")
        self.assertEqual(row(res, "keyframe interval")["verdict"], "FAIL")
        prof = write_profile(self.root, adv=self.adv(Encoder="h264_texture_amf"),
                             stream_enc={"rate_control": "CBR", "keyint_sec": 2})
        res = obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 6700 XT")
        self.assertEqual(row(res, "stream rate control")["verdict"], "PASS")
        self.assertEqual(row(res, "keyframe interval")["verdict"], "PASS")

    def test_stream_key_never_in_output(self):
        prof = write_profile(self.root, adv=self.adv(Encoder="h264_texture_amf"),
                             stream_enc={"rate_control": "CBR", "keyint_sec": 2},
                             service={"type": "rtmp_common", "settings": {"service": "Example Service",
                                                                          "key": "live_SECRET123", "server": "auto"}})
        res = obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 6700 XT")
        self.assertNotIn("live_SECRET123", json.dumps(res))
        self.assertEqual(res["service"]["type"], "rtmp_common")

    def test_record_format(self):
        prof = write_profile(self.root, adv=self.adv(RecFormat2="mp4"))
        self.assertEqual(row(obs_audit.audit_profile(prof), "recording format")["verdict"], "FAIL")
        prof = write_profile(self.root, adv=self.adv(RecFormat2="hybrid_mp4"))
        self.assertEqual(row(obs_audit.audit_profile(prof), "recording format")["verdict"], "PASS")

    def test_vod_track(self):
        prof = write_profile(self.root, adv=self.adv())
        self.assertEqual(row(obs_audit.audit_profile(prof), "VOD track")["verdict"], "PASS")
        prof = write_profile(self.root, adv=self.adv(VodTrackIndex="1"))
        self.assertEqual(row(obs_audit.audit_profile(prof), "VOD track")["verdict"], "FAIL")

    def test_amf_bframes_by_version(self):
        prof = write_profile(self.root, adv=self.adv(Encoder="h264_texture_amf"),
                             stream_enc={"rate_control": "CBR", "keyint_sec": 2, "bf": 2})
        old = obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 6700 XT", obs_version="32.2.1")
        self.assertEqual(row(old, "AMF B-frames")["verdict"], "FAIL")
        new = obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 6700 XT", obs_version="32.2.2")
        self.assertEqual(row(new, "AMF B-frames")["verdict"], "PASS")
        unknown = obs_audit.audit_profile(prof, gpu_name="AMD Radeon RX 6700 XT")
        self.assertEqual(row(unknown, "AMF B-frames")["verdict"], "NOT-RUN")


# ---- obs_post: chapters, moments, marks, sheet ----------------------------------------------

class ChapterTests(unittest.TestCase):
    def test_rules_applied(self):
        marks = [{"t": 5, "label": "early"}, {"t": 300, "label": "boss"}, {"t": 304, "label": "dup"},
                 {"t": 900, "label": "end fight"}]
        r = obs_post.chapters(marks, 1200)
        self.assertEqual(r["verdict"], "PASS")
        self.assertTrue(r["lines"][0].startswith("00:00 "))
        times = [c["t"] for c in r["chapters"]]
        self.assertGreaterEqual(len(times), 3)
        for a, b in zip(times, times[1:] + [1200]):
            self.assertGreaterEqual(b - a, 10)

    def test_too_few_fails(self):
        r = obs_post.chapters([{"t": 400, "label": "only"}], 1200)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("fewer than 3", r["reason"])

    def test_marks_past_end_dropped(self):
        r = obs_post.chapters([{"t": 100, "label": "a"}, {"t": 200, "label": "b"}, {"t": 5000, "label": "x"}], 600)
        self.assertNotIn("x", " ".join(r["lines"]))

    def test_hours_format(self):
        r = obs_post.chapters([{"t": 1800, "label": "a"}, {"t": 3700, "label": "b"}], 4000)
        self.assertIn("1:01:40 b", r["lines"])


class MomentTests(unittest.TestCase):
    def test_mark_plus_peak_outranks_lone_keyword(self):
        marks = [{"t": 600, "label": "clutch"}]
        peaks = [{"t": 605, "lufs": -8.0}]
        segments = [{"start": 1500, "end": 1504, "text": "that was insane"}]
        out = obs_post.rank_moments(marks, segments, ["insane"], peaks, clip_len=40, max_len=60)
        self.assertEqual(len(out), 2)
        self.assertLess(abs(out[0]["center"] - 600), 10)
        for m in out:
            self.assertLessEqual(m["end"] - m["start"], 60)
            self.assertTrue(m["reasons"])

    def test_cooldown_merges_neighbours(self):
        marks = [{"t": 100, "label": "a"}, {"t": 110, "label": "b"}]
        out = obs_post.rank_moments(marks, [], [], [], clip_len=30, max_len=60)
        self.assertEqual(len(out), 1)


class MarkAndSheetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_mark_and_read_back(self):
        side = self.root / "obsrunner-marks.jsonl"
        obs_post.append_mark(side, 61500, "good play")
        obs_post.append_mark(side, 125000, "funny")
        marks = obs_post.read_marks(side)
        self.assertEqual([m["t"] for m in marks], [61.5, 125.0])
        self.assertEqual(marks[0]["label"], "good play")

    def test_sheet_slots_and_no_overwrite(self):
        clip = self.root / "clip.mp4"
        clip.write_bytes(b"x")
        r = obs_post.write_sheet(clip, chapters_lines=["00:00 Intro", "02:00 A", "05:00 B"])
        text = Path(r["path"]).read_text(encoding="utf-8")
        for slot in ("Title", "Description", "Made for kids", "Altered or synthetic", "Paid promotion"):
            self.assertIn(slot, text)
        self.assertIn("UNSET", text)
        self.assertIn("00:00 Intro", text)
        r2 = obs_post.write_sheet(clip, chapters_lines=[])
        self.assertEqual(r2["status"], "REFUSED")


class ArgTests(unittest.TestCase):
    def test_vertical_crop_and_scale(self):
        args = obs_post.build_args("vertical", Path("in.mkv"), Path("out.mp4"),
                                   {"crop": "608:1080:656:0", "encoder": "libx264"})
        vf = args[args.index("-vf") + 1]
        self.assertIn("crop=608:1080:656:0", vf)
        self.assertIn("scale=1080:1920", vf)
        self.assertIn("yuv420p", args)

    def test_captions_escape_windows_path(self):
        args = obs_post.build_args("captions", Path("in.mkv"), Path("out.mp4"),
                                   {"srt": "C" + r":\clips\a b.srt", "encoder": "libx264"})
        vf = args[args.index("-vf") + 1]
        self.assertIn(r"subtitles='C\:/clips/a b.srt'", vf)

    def test_captions_refuse_apostrophe_in_filter(self):
        # K7-5-09: FFmpeg honours no escape inside a quoted filter value, so an apostrophe never reaches -vf.
        with self.assertRaises(ValueError):
            obs_post.build_args("captions", Path("in.mkv"), Path("out.mp4"),
                                {"srt": "C" + r":\clips\it's.srt", "encoder": "libx264"})

    def test_stage_srt_copies_apostrophe_path_to_plain_name(self):
        self.assertEqual(obs_post.stage_srt("clips/a.srt"), ("clips/a.srt", None))
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "it's here.srt"
            src.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n", encoding="utf-8")
            staged, tmp = obs_post.stage_srt(str(src))
            try:
                self.assertNotIn("'", staged)
                self.assertEqual(Path(staged).read_text(encoding="utf-8"), src.read_text(encoding="utf-8"))
                vf = obs_post.build_args("captions", Path("in.mkv"), Path("out.mp4"),
                                         {"srt": staged, "encoder": "libx264"})
                self.assertTrue(any(x.startswith("subtitles='") for x in vf))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        with self.assertRaises(ValueError):
            obs_post.stage_srt("nowhere/it's.srt")

    def test_parse_time_accepts_clock_and_seconds(self):
        self.assertEqual(obs_post.parse_time("01:02:03.5"), 3723.5)
        self.assertEqual(obs_post.parse_time("02:03"), 123.0)
        self.assertEqual(obs_post.parse_time("42"), 42.0)

    def test_cut_uses_times(self):
        args = obs_post.build_args("cut", Path("in.mkv"), Path("out.mp4"),
                                   {"start": "10", "end": "20", "encoder": "libx264"})
        self.assertIn("-ss", args)
        self.assertIn("-to", args)
        self.assertEqual(args[-1], "out.mp4")


# ---- obs_post: renders with fake tools ----------------------------------------------------

class RenderTests(StateDirCase):
    def setUp(self):
        super().setUp()
        self.ffmpeg = self.root / "fake_ffmpeg.py"
        self.ffprobe = self.root / "fake_ffprobe.py"
        self.ffmpeg.write_text(FAKE_FFMPEG, encoding="utf-8")
        self.ffprobe.write_text(FAKE_FFPROBE, encoding="utf-8")
        self.inp = self.root / "rec.mkv"
        self.inp.write_bytes(b"fixture recording")
        self._penv = {k: os.environ.get(k) for k in ("FAKE_PIX", "FAKE_DUR", "FAKE_FFMPEG_LOG")}

    def tearDown(self):
        for k, v in self._penv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        super().tearDown()

    def run_post(self, *extra):
        cmd = [sys.executable, str(HERE / "obs_post.py"), "--ffmpeg", str(self.ffmpeg),
               "--ffprobe", str(self.ffprobe)] + list(extra)
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.stderr.strip(), "", p.stderr)
        return json.loads(p.stdout)

    def test_cut_writes_receipt_with_hashes(self):
        out = self.root / "out1"
        r = self.run_post("cut", str(self.inp), "--out", str(out), "--start", "0", "--end", "10",
                          "--encoder", "libx264", "--obs-state", "idle")
        self.assertEqual(r["verdict"], "PASS", r)
        rec = [json.loads(l) for l in (out / "receipts.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rec), 1)
        self.assertEqual(len(rec[0]["input_sha256"]), 64)
        self.assertEqual(len(rec[0]["output_sha256"]), 64)
        self.assertEqual(rec[0]["probe"]["pix_fmt"], "yuv420p")
        self.assertEqual(rec[0]["probe"]["audio"], "aac")
        self.assertFalse(self.lease_path().exists())  # CPU encode takes no lease

    def test_yuv444_output_fails(self):
        os.environ["FAKE_PIX"] = "yuv444p"
        r = self.run_post("cut", str(self.inp), "--out", str(self.root / "out2"), "--start", "0", "--end", "10",
                          "--encoder", "libx264", "--obs-state", "idle")
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("pix_fmt", " ".join(r["reasons"]))

    def test_duration_off_by_more_than_a_frame_fails(self):
        os.environ["FAKE_DUR"] = "9.5"
        r = self.run_post("cut", str(self.inp), "--out", str(self.root / "out3"), "--start", "0", "--end", "10",
                          "--encoder", "libx264", "--obs-state", "idle")
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("duration", " ".join(r["reasons"]))

    def test_existing_out_folder_refused(self):
        out = self.root / "exists"
        out.mkdir()
        r = self.run_post("cut", str(self.inp), "--out", str(out), "--start", "0", "--end", "10",
                          "--encoder", "libx264", "--obs-state", "idle")
        self.assertEqual(r["verdict"], "REFUSED")
        self.assertIn("overwrite", r["reasons"][0])

    def test_gpu_encode_refused_while_obs_live(self):
        r = self.run_post("cut", str(self.inp), "--out", str(self.root / "o4"), "--start", "0", "--end", "10",
                          "--encoder", "h264_amf", "--obs-state", "live")
        self.assertEqual(r["verdict"], "REFUSED")
        self.assertIn("OBS is encoding", r["reasons"][0])

    def test_gpu_encode_refused_when_lease_held(self):
        t = datetime.now(timezone.utc)
        self.lease_path().write_text(json.dumps({"holder": "comfyrunner", "purpose": "render",
                                                 "started": t.isoformat(),
                                                 "expires": (t + timedelta(minutes=30)).isoformat()}),
                                     encoding="utf-8")
        r = self.run_post("cut", str(self.inp), "--out", str(self.root / "o5"), "--start", "0", "--end", "10",
                          "--encoder", "h264_amf", "--obs-state", "idle")
        self.assertEqual(r["verdict"], "REFUSED")
        self.assertIn("GPU busy", r["reasons"][0])

    def test_gpu_encode_takes_and_releases_lease(self):
        r = self.run_post("cut", str(self.inp), "--out", str(self.root / "o6"), "--start", "0", "--end", "10",
                          "--encoder", "h264_amf", "--obs-state", "idle")
        self.assertEqual(r["verdict"], "PASS", r)
        self.assertEqual(r["lease"]["holder"], "obsrunner")
        self.assertFalse(self.lease_path().exists())

    def test_loudness_two_pass_uses_measured_values(self):
        log = self.root / "ff.log"
        os.environ["FAKE_FFMPEG_LOG"] = str(log)
        r = self.run_post("loudness", str(self.inp), "--out", str(self.root / "o7"), "--lufs", "-14",
                          "--encoder", "libx264", "--obs-state", "idle")
        self.assertEqual(r["verdict"], "PASS", r)
        calls = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
        final = " ".join(calls[-1])
        self.assertIn("measured_I=-23.10", final)
        self.assertIn("I=-14", final)

    def test_hold_and_release(self):
        h = self.run_post("hold", "--hours", "3")
        self.assertEqual(h["status"], "HELD")
        lease = json.loads(self.lease_path().read_text(encoding="utf-8"))
        self.assertEqual(lease["holder"], "obsrunner")
        rel = self.run_post("release")
        self.assertEqual(rel["status"], "RELEASED")
        self.assertFalse(self.lease_path().exists())

    def test_hold_records_ram_estimate_or_says_unknown(self):
        # Owner Q24: a GPU holder writes est_ram_bytes; unknown is null and said so, never zero.
        h = self.run_post("hold", "--hours", "1", "--est-ram-gib", "3")
        lease = json.loads(self.lease_path().read_text(encoding="utf-8"))
        self.assertEqual(lease["est_ram_bytes"], 3 * 1024 ** 3)
        self.run_post("release")
        h = self.run_post("hold", "--hours", "1")
        lease = json.loads(self.lease_path().read_text(encoding="utf-8"))
        self.assertIsNone(lease["est_ram_bytes"])
        self.assertIn("est_ram_bytes unknown", h["note"])
        self.run_post("release")

    def test_render_lease_carries_a_ram_estimate(self):
        r = self.run_post("cut", str(self.inp), "--out", str(self.root / "o8"), "--start", "0", "--end", "10",
                          "--encoder", "h264_amf", "--obs-state", "idle")
        self.assertEqual(r["lease"]["est_ram_bytes"], obs_post.RENDER_RAM_BYTES)

    def test_release_never_deletes_another_holders_lease(self):
        t = datetime.now(timezone.utc)
        self.lease_path().write_text(json.dumps({"holder": "comfyrunner", "expires":
                                                 (t + timedelta(minutes=30)).isoformat()}), encoding="utf-8")
        rel = self.run_post("release")
        self.assertEqual(rel["status"], "NOT-OURS")
        self.assertTrue(self.lease_path().exists())


if __name__ == "__main__":
    unittest.main()
