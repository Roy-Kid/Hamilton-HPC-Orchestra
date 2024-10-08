from h_submitor.base import cmdline

class TestCMDLine:

    def test_cmdline(self):

        @cmdline
        def worker(second: int) -> int:
            print(f"start work {second}s")
            result = yield {
                'cmd': [f"echo", f"{second}"],
                'block': True,
            }
            print(result)
            return result

        assert worker(3).stdout.decode().strip() == "3"