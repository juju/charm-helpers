import sys
import mock

sys.modules['yum'] = mock.MagicMock()
