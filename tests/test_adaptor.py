from h_submitor.submitor import SlurmSubmitor
from pytest_mock import MockerFixture
from unittest.mock import MagicMock
import subprocess
import pytest
from pathlib import Path


class MockedSlurm:

    @staticmethod
    def run(cmd, capture_output) -> subprocess.CompletedProcess:

        if cmd[0] == "sbatch":
            return MockedSlurm.sbatch(cmd)
        elif cmd[0] == "squeue":
            return MockedSlurm.squeue(cmd)
        elif cmd[0] == "scancel":
            return MockedSlurm.scancel(cmd)
    
    @staticmethod
    def sbatch(cmd):

        mock = MagicMock()
        mock.returncode = 0
        if cmd[-1] == "--test-only":
            mock.stderr = f"sbatch: Job 3676091 to start at 2024-04-26T20:02:12 using 256 processors on nodes nid001000 in partition main"

        else:
            mock.stdout = "3676091"

        return mock
    
    @staticmethod
    def squeue(cmd):

        mock = MagicMock()
        mock.stdout = "JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)\n3676091      main     test     user  R       0:01      1 nid001000"
        return mock
    
    @staticmethod
    def scancel(cmd):

        mock = MagicMock()
        mock.stdout = "Job 3676091 has been cancelled."
        return mock


class TestSlurmAdapter:

    @pytest.fixture(scope='class', autouse=True)
    def delete_script(self):
        yield
        script_path = Path("run_slurm.sh")
        if script_path.exists():
            script_path.unlink()

    def test_gen_script(self):

        submitor = SlurmSubmitor("test_submitor")
        config = {"--job-name": "test", "--ntasks": 1}
        path = submitor.gen_script(script_path="run_slurm.sh", cmd=["ls"], **config)
        with open(path, "r") as f:
            lines = f.readlines()

        assert lines[0] == "#!/bin/bash\n"
        assert lines[1] == "#SBATCH --job-name=test\n"
        assert lines[2] == "#SBATCH --ntasks=1\n"
        assert lines[3] == "\n"
        assert lines[4] == "ls"

    def test_submit(self, mocker: MockerFixture):

        mocker.patch.object(subprocess, "run", MockedSlurm.run)

        submitor = SlurmSubmitor("test_submitor")
        job_id = submitor.submit(cmd=["ls"], job_name="test", n_cores=1)
        assert isinstance(job_id, int)

    def test_submit_test_only(self, mocker: MockerFixture):

        mocker.patch.object(subprocess, "run", MockedSlurm.run)

        submitor = SlurmSubmitor("test_submitor")
        job_id = submitor.submit(cmd=["ls"], job_name="test", n_cores=1, test_only=True)
        assert isinstance(job_id, int)

    def test_monitoring(self, mocker: MockerFixture):

        mocker.patch.object(subprocess, "run", MockedSlurm.run)

        submitor = SlurmSubmitor("test_submitor")
        job_id = submitor.submit(cmd=["sleep 1"], job_name="test1", n_cores=1, is_block=False)  # not block inplace
        submitor.monitor(interval=1)  # block here
        assert isinstance(job_id, int)