from datetime import date, datetime

import xlsxwriter
from django.http import HttpResponse


class ExcelExporter:
    """Generic class to export an xlsx file"""

    date_format = None
    header_format = None
    default_format = None

    def get_filename(self):
        raise NotImplementedError

    def get_file_title(self):
        raise NotImplementedError

    def generate(self, workbook):
        """
        Fonction a implementer pour appeler add_sheet avec vos données

        :param workbook: Instance de workbook de xlsxwritter
        """
        raise NotImplementedError

    def _safe_sheet_name(self, name: str) -> str:
        for ch in ["\\", "/", "*", "?", ":", "[", "]"]:
            name = name.replace(ch, "-")
        name = (name or "Feuille").strip()
        return name[:31]

    def _excell_cell_type(self, value):
        # Booléen
        if isinstance(value, bool):
            return "Oui" if value else "Non", self.default_format

        # Date/Datetime
        if isinstance(value, (date, datetime)):
            return value, self.date_format

        # None
        if value is None:
            return "", self.default_format

        # Autres types -> string standard
        return value, self.default_format

    def add_sheet(self, workbook, sheet_name, table_name, headers, rows):
        if not headers:
            raise ValueError("Headers cannot be empty")

        ws = workbook.add_worksheet(self._safe_sheet_name(sheet_name))

        ws.write_row(
            0,
            0,
            headers,
        )
        ws.set_row(0, None, self.header_format)

        row_index = 1

        for row in rows:
            for col, v in enumerate(row):
                value, format = self._excell_cell_type(v)
                ws.write(row_index, col, value, format)
            row_index += 1

        ws.add_table(
            0,
            0,
            row_index - 1,
            len(headers) - 1,
            {
                "header_row": True,
                "autofilter": True,
                "name": table_name,
                "style": None,
                "columns": [{"header": h} for h in headers],
            },
        )
        ws.autofit()

    def get(self, request, *args, **kwargs):
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{self.get_filename()}"'
            },
        )
        workbook = xlsxwriter.Workbook(response)
        self.date_format = workbook.add_format(
            {"num_format": "dd/mm/yyyy", "font_size": 12}
        )
        self.header_format = workbook.add_format({"bold": True, "font_size": 12})
        self.default_format = workbook.add_format({"font_size": 12})
        workbook.set_properties({"title": self.get_file_title()})
        self.generate(workbook)
        workbook.close()
        return response
