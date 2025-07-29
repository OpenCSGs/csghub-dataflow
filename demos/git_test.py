from pycsghub.repository import Repository

token = "9eba3d0173eb48ed99bb6952233bbb50"
# token = None

# path = r'D:\work\workspace\block\data-flow\temp_format\10eb27ee-aef2-4ba3-bb0b-d68765437f7d\work_test\test_to'
path = r'D:\work\workspace\block\data-flow\datasource\json\4cb46199-3a16-4879-8471-e435c00bbee3'
work_dir = r'D:\work\workspace\block\data-flow\datasource\json\work'


r = Repository(
    repo_id="z275748353/lambert_test",
    upload_path=path,
    user_name="z275748353",
    token=token,
    repo_type="dataset",
    branch_name="datasource_test",
    endpoint="http://home.sxcfx.cn:18120",
    work_dir=work_dir,
)

r.upload()