"""
UBX Protocol handler

Uses pyubx2 library for parsing

Created on 30 Sep 2020

@author: semuadmin
"""
# pylint: disable=invalid-name

from datetime import datetime
from pyubx2 import UBXMessage, POLL, UBX_MSGIDS, UBX_CONFIG_MESSAGES

CFG_MSG_OFF = b"\x00\x00\x00\x00\x00\x01"
CFG_MSG_ON = b"\x01\x01\x01\x01\x01\x01"
BOTH = 3
UBX = 1
NMEA = 2


class UBXHandler:
    """
    UBXHandler class
    """

    def __init__(self, app):
        """
        Constructor.

        :param app: reference to main tkinter application
        """

        self.__app = app  # Reference to main application class
        self.__master = self.__app.get_master()  # Reference to root class (Tk)

        self._raw_data = None
        self._parsed_data = None
        self._record_track = False
        self.gsv_data = (
            []
        )  # Holds array of current satellites in view from NMEA GSV sentences
        self.lon = 0
        self.lat = 0
        self.alt = 0
        self.track = 0
        self.speed = 0
        self.pdop = 0
        self.hdop = 0
        self.vdop = 0
        self.hacc = 0
        self.vacc = 0
        self.utc = ""
        self.sip = 0
        self.fix = "-"
        self.ubx_baudrate = 9600
        self.ubx_inprot = 7
        self.ubx_outprot = 3

    @staticmethod
    def poll_ubx_config(serial):
        """
        POLL current UBX device configuration (port protocols
        and software version).

        NB: The responses and acknowledgements to these polls
        may take several seconds to arrive, particularly in
        heavy traffic.

        :param serial
        """

        for msgtype in ("CFG-PRT", "MON-VER"):
            msg = UBXMessage(msgtype[0:3], msgtype, POLL)
            serial.write(msg.serialize())

    def process_data(self, data: bytes) -> UBXMessage:
        """
        Process UBX message type

        :param data: bytes

        :return UBX message as UBXMessage:
        """

        parsed_data = UBXMessage.parse(data, False)

        if parsed_data.identity == "ACK-ACK":
            self._process_ACK_ACK(parsed_data)
        if parsed_data.identity == "ACK-NAK":
            self._process_ACK_NAK(parsed_data)
        if parsed_data.identity == "CFG-MSG":
            self._process_CFG_MSG(parsed_data)
        if parsed_data.identity == "CFG-PRT":
            self._process_CFG_PRT(parsed_data)
        if parsed_data.identity == "CFG-INF":
            self._process_CFG_INF(parsed_data)
        if parsed_data.identity == "NAV-POSLLH":
            self._process_NAV_POSLLH(parsed_data)
        if parsed_data.identity == "NAV-PVT":
            self._process_NAV_PVT(parsed_data)
        if parsed_data.identity == "NAV-VELNED":
            self._process_NAV_VELNED(parsed_data)
        if parsed_data.identity == "NAV-SVINFO":
            self._process_NAV_SVINFO(parsed_data)
        if parsed_data.identity == "NAV-SOL":
            self._process_NAV_SOL(parsed_data)
        if parsed_data.identity == "NAV-DOP":
            self._process_NAV_DOP(parsed_data)
        if parsed_data.identity == "MON-VER":
            self._process_MON_VER(parsed_data)
        if data or parsed_data:
            self._update_console(data, parsed_data)

        return parsed_data

    def _update_console(self, raw_data: bytes, parsed_data: UBXMessage):
        """
        Write the incoming data to the console in raw or parsed format.

        :param raw_data: bytes
        :param parsed_data: UBXMessage
        """

        if self.__app.frm_settings.get_settings()["raw"]:
            self.__app.frm_console.update_console(str(raw_data))
        else:
            self.__app.frm_console.update_console(str(parsed_data))

    def _process_ACK_ACK(self, data: UBXMessage):
        """
        Process CFG-MSG sentence - UBX message configuration.

        :param data: UBXMessage
        """

        msgtype = UBX_MSGIDS[self.msgclass2bytes(data.clsID, data.msgID)]

        # update the UBX config panel
        if self.__app.dlg_ubxconfig is not None:
            self.__app.dlg_ubxconfig.update("ACK-ACK", msgtype=msgtype)

    def _process_ACK_NAK(self, data: UBXMessage):
        """
        Process CFG-MSG sentence - UBX message configuration.

        :param data: UBXMessage
        """

        msgtype = UBX_MSGIDS[self.msgclass2bytes(data.clsID, data.msgID)]

        # update the UBX config panel
        if self.__app.dlg_ubxconfig is not None:
            self.__app.dlg_ubxconfig.update("ACK-NAK", msgtype=msgtype)

    def _process_CFG_MSG(self, data: UBXMessage):
        """
        Process CFG-MSG sentence - UBX message configuration.

        :param data: UBXMessage
        """

        msgtype = UBX_CONFIG_MESSAGES[self.msgclass2bytes(data.msgClass, data.msgID)]
        ddcrate = data.rateDDC
        uart1rate = data.rateUART1
        uart2rate = data.rateUART2
        usbrate = data.rateUSB
        spirate = data.rateSPI

        # update the UBX config panel
        if self.__app.dlg_ubxconfig is not None:
            self.__app.dlg_ubxconfig.update(
                "CFG-MSG",
                msgtype=msgtype,
                ddcrate=ddcrate,
                uart1rate=uart1rate,
                uart2rate=uart2rate,
                usbrate=usbrate,
                spirate=spirate,
            )

    def _process_CFG_INF(self, data: UBXMessage):
        """
        Process CFG-INF sentence - UBX info message configuration.

        :param data: UBXMessage
        """

        # update the UBX config panel
        if self.__app.dlg_ubxconfig is not None:
            self.__app.dlg_ubxconfig.update("CFG-INF")

    def _process_CFG_PRT(self, data: UBXMessage):
        """
        Process CFG-PRT sentence - UBX port configuration.

        :param data: UBXMessage
        """

        self.ubx_baudrate = data.baudRate
        self.ubx_inprot = int.from_bytes(data.inProtoMask, "little", signed=False)
        self.ubx_outprot = int.from_bytes(data.outProtoMask, "little", signed=False)

        # update the UBX config panel
        if self.__app.dlg_ubxconfig is not None:
            self.__app.dlg_ubxconfig.update(
                "CFG-PRT",
                baudrate=self.ubx_baudrate,
                inprot=self.ubx_inprot,
                outprot=self.ubx_outprot,
            )

    def _process_NAV_POSLLH(self, data: UBXMessage):
        """
        Process NAV-LLH sentence - Latitude, Longitude, Height.

        :param data: UBXMessage
        """

        try:
            self.utc = UBXMessage.itow2utc(data.iTOW)
            self.lat = data.lat / 10 ** 7
            self.lon = data.lon / 10 ** 7
            self.alt = data.hMSL / 1000
            self.hacc = data.hAcc / 1000
            self.vacc = data.vAcc / 1000
            self.__app.frm_banner.update_banner(
                time=self.utc,
                lat=self.lat,
                lon=self.lon,
                alt=self.alt,
                hacc=self.hacc,
                vacc=self.vacc,
            )

            self.__app.frm_mapview.update_map(self.lat, self.lon, self.hacc)

        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_PVT(self, data: UBXMessage):
        """
        Process NAV-PVT sentence -  Navigation position velocity time solution.

        :param data: UBXMessage
        """

        try:
            self.utc = UBXMessage.itow2utc(data.iTOW)
            self.lat = data.lat / 10 ** 7
            self.lon = data.lon / 10 ** 7
            self.alt = data.hMSL / 1000
            self.hacc = data.hAcc / 1000
            self.vacc = data.vAcc / 1000
            self.pdop = data.pDOP / 100
            self.sip = data.numSV
            self.speed = data.gSpeed / 1000  # m/s
            self.track = data.headMot / 10 ** 5
            fix = UBXMessage.gpsfix2str(data.fixType)
            self.__app.frm_banner.update_banner(
                time=self.utc,
                lat=self.lat,
                lon=self.lon,
                alt=self.alt,
                hacc=self.hacc,
                vacc=self.vacc,
                dop=self.pdop,
                sip=self.sip,
                speed=self.speed,
                fix=fix,
                track=self.track,
            )

            self.__app.frm_mapview.update_map(self.lat, self.lon, self.hacc)

            if (
                self.__app.frm_settings.get_settings()["recordtrack"]
                and self.lat != ""
                and self.lon != ""
            ):
                time = (
                    datetime(
                        data.year,
                        data.month,
                        data.day,
                        data.hour,
                        data.min,
                        data.second,
                    ).isoformat()
                    + "Z"
                )
                if fix == "3D":
                    fix = "3d"
                elif fix == "2D":
                    fix = "2d"
                else:
                    fix = "none"
                self.__app.file_handler.add_trackpoint(
                    self.lat,
                    self.lon,
                    ele=self.alt,
                    time=time,
                    fix=fix,
                    sat=self.sip,
                    pdop=self.pdop,
                )
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_VELNED(self, data: UBXMessage):
        """
        Process NAV-VELNED sentence - Velocity Solution in North East Down format.

        :param data: UBXMessage
        """

        try:
            self.track = data.heading / 10 ** 5
            self.speed = data.gSpeed / 100  # m/s
            self.__app.frm_banner.update_banner(speed=self.speed, track=self.track)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_SVINFO(self, data: UBXMessage):
        """
        Process NAV-SVINFO sentences - Space Vehicle Information.

        :param data: UBXMessage
        """

        try:
            self.gsv_data = []
            num_siv = int(data.numCh)
            self.__app.frm_banner.update_banner(siv=num_siv)

            for i in range(num_siv):
                idx = "_{0:0=2d}".format(i + 1)
                svid = getattr(data, "svid" + idx)
                elev = getattr(data, "elev" + idx)
                azim = getattr(data, "azim" + idx)
                cno = getattr(data, "cno" + idx)
                self.gsv_data.append((svid, elev, azim, cno))
            self.__app.frm_satview.update_sats(self.gsv_data)
            self.__app.frm_graphview.update_graph(self.gsv_data, num_siv)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_SOL(self, data: UBXMessage):
        """
        Process NAV-SOL sentence - Navigation Solution.

        :param data: UBXMessage
        """

        try:
            self.pdop = data.pDOP / 100
            self.sip = data.numSV
            fix = UBXMessage.gpsfix2str(data.gpsFix)

            self.__app.frm_banner.update_banner(dop=self.pdop, fix=fix, sip=self.sip)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_DOP(self, data: UBXMessage):
        """
        Process NAV-DOP sentence - Dilution of Precision.

        :param data: UBXMessage
        """

        try:
            self.pdop = data.pDOP / 100
            self.hdop = data.hDOP / 100
            self.vdop = data.vDOP / 100

            self.__app.frm_banner.update_banner(
                dop=self.pdop, hdop=self.hdop, vdop=self.vdop
            )
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_MON_VER(self, data: UBXMessage):
        """
        Process MON-VER sentence - Receiver Software / Hardware version information.

        :param data: UBXMessage
        """

        exts = []
        fw_version = "n/a"
        protocol = "n/a"
        gnss_supported = ""

        try:
            sw_version = (
                getattr(data, "swVersion", "n/a").replace(b"\x00", b"").decode("utf-8")
            )
            sw_version = sw_version.replace("ROM CORE", "ROM")
            sw_version = sw_version.replace("EXT CORE", "Flash")
            hw_version = (
                getattr(data, "hwVersion", "n/a").replace(b"\x00", b"").decode("utf-8")
            )

            for i in range(4):
                idx = "_{0:0=2d}".format(i + 1)
                exts.append(
                    getattr(data, "extension" + idx, b"")
                    .replace(b"\x00", b"")
                    .decode("utf-8")
                )
                if "FWVER=" in exts[i]:
                    fw_version = exts[i].replace("FWVER=", "")
                if "PROTVER=" in exts[i]:
                    protocol = exts[i].replace("PROTVER=", "")
                if "PROTVER " in exts[i]:
                    protocol = exts[i].replace("PROTVER ", "")
                for gnss in ("GPS", "GLO", "GAL", "BDS", "SBAS", "IMES", "QZSS"):
                    if gnss in exts[i]:
                        gnss_supported = gnss_supported + gnss + " "

            # update the UBX config panel
            if self.__app.dlg_ubxconfig is not None:
                self.__app.dlg_ubxconfig.update(
                    "MON-VER",
                    swversion=sw_version,
                    hwversion=hw_version,
                    fwversion=fw_version,
                    protocol=protocol,
                    gnsssupported=gnss_supported,
                )

        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    @staticmethod
    def msgclass2bytes(msgClass: int, msgID: int) -> bytes:
        """
        Convert message class/id integers to bytes.

        :param msgCLass: int
        :param msgID: int

        :return message class as string: str
        """

        msgClass = msgClass.to_bytes(1, byteorder="little", signed=False)
        msgID = msgID.to_bytes(1, byteorder="little", signed=False)
        return msgClass + msgID
