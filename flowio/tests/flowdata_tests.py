import shutil
import unittest
import os
import io
import tempfile
from flowio import FlowData
from flowio.exceptions import DataOffsetDiscrepancyError


class FlowDataTestCase(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.flow_data = FlowData('examples/fcs_files/3FITC_4PE_004.fcs')
        self.flow_data_spill = FlowData('examples/fcs_files/100715.fcs')

    def test_string_representation(self):
        self.assertEqual(
            str(self.flow_data),
            "FlowData(3FITC_4PE_004.fcs)"
        )

    def test_event_count(self):
        self.assertEqual(
            len(self.flow_data.events) / self.flow_data.channel_count,
            int(self.flow_data.text['tot'])
        )

    def test_get_text(self):
        self.assertEqual(self.flow_data.text['cyt'], 'FACScan')

    def test_load_only_text(self):
        flow_data = FlowData('examples/fcs_files/3FITC_4PE_004.fcs', only_text=True)

        self.assertIsNone(flow_data.events)
        self.assertRaises(AttributeError, flow_data.write_fcs, 'delete_this_file.fcs')

    @staticmethod
    def test_load_fcs_from_memory():
        with open('examples/fcs_files/3FITC_4PE_004.fcs', 'rb') as f:
            mem_file = io.BytesIO(f.read())
            FlowData(mem_file)

    def test_load_temp_file(self):
        with tempfile.TemporaryFile() as tmp_file:
            with open('examples/fcs_files/3FITC_4PE_004.fcs', 'r+b') as f:
                shutil.copyfileobj(f, tmp_file)
            tmp_file.seek(0)
            out_data = FlowData(tmp_file)
        self.assertIsInstance(out_data, FlowData)

    def test_load_non_file_input(self):
        non_file = object()
        self.assertRaises(AttributeError, FlowData, non_file)

    def test_write_fcs(self):
        file_name = 'flowio/tests/flowio_test_write_fcs.fcs'
        self.flow_data_spill.write_fcs(file_name)

        fcs_export = FlowData(file_name)

        self.assertIsInstance(fcs_export, FlowData)
        os.unlink(file_name)

    def test_parse_var_int_data(self):
        event_values = [
            49135, 61373, 48575, 49135, 61373, 48575, 7523, 598, 49135, 61373,
            48575, 49135, 61373, 48575, 28182, 61200, 48575, 49135, 32445, 30797,
            19057, 49135, 61373, 48575, 5969, 8265081,
            61266, 48575, 49135, 20925, 61265, 48575, 27961, 25200, 61287, 48575, 9795,
            49135, 29117, 49135, 61373, 48575, 61228, 48575, 22, 21760, 49135,
            20413, 49135, 23997, 19807, 15691602
        ]

        # To double-check our logic, let's use the 2 values from
        # channel 26 where:
        # PnB is 32
        # PnR is 11209599
        # The 1st value for chan 26, 32-bit, unmasked:  142482809
        # The 2nd value for chan 26, 32-bit, unmasked: 3220139858
        # The next power of 2 above 11209599 (PnR) is:   16777216
        # Subtracting 1 from this power of 2, we can see what the
        # new values should be from the binary:
        #   1st value:
        #   0000 1000 0111 1110 0001 1101 0111 1001     142482809 (orig 32-bit value)
        #   0000 0000 1111 1111 1111 1111 1111 1111      16777215 (2 ** 24 - 1)
        #   0000 0000 0111 1110 0001 1101 0111 1001       8265081 (new value)
        #   2nd value:
        #   1011 1111 1110 1111 0110 1111 0101 0010    3220139858 (orig 32-bit value)
        #   0000 0000 1111 1111 1111 1111 1111 1111      16777215 (2 ** 24 - 1)
        #   0000 0000 1110 1111 0110 1111 0101 0010      15691602 (new value)

        fcs_file = "examples/fcs_files/variable_int_example.fcs"
        sample = FlowData(fcs_file)

        self.assertListEqual(event_values, sample.events)

    def test_write_fcs_preserves_channels(self):
        orig_fd = FlowData('examples/fcs_files/100715.fcs')
        expected = orig_fd.channels

        with tempfile.NamedTemporaryFile() as tmpfile:
            orig_fd.write_fcs(tmpfile.name)
            out_data = FlowData(tmpfile.name)
            actually = out_data.channels

            self.assertDictEqual(expected, actually)

    def test_issue_03(self):
        """
        Tests Attune FCS files for error in FlowData method parse_float_data:

        flowio/flowdata.py in __parse_float_data(self, offset, start, stop, data_type, order)
            256
            257         tmp = unpack('%s%d%s' % (order, num_items, data_type),
        --> 258                      self.__read_bytes(offset, start, stop))
            259         return tmp
            260

        error: unpack requires a buffer of 277676 bytes
        """
        flow_data = FlowData('examples/fcs_files/G11.fcs')

        self.assertIsInstance(flow_data, FlowData)

    def test_data_start_offset_discrepancy(self):
        fcs_file = "examples/fcs_files/data_start_offset_discrepancy_example.fcs"
        self.assertRaises(DataOffsetDiscrepancyError, FlowData, fcs_file)

    def test_data_stop_offset_discrepancy(self):
        fcs_file = "examples/fcs_files/data_stop_offset_discrepancy_example.fcs"
        self.assertRaises(DataOffsetDiscrepancyError, FlowData, fcs_file)
