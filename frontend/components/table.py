from fasthtml.common import *
from dataclasses import dataclass
import json

@dataclass
class DataTable:
    content: dict
    
    def __ft__(self):
        return Script('''
                        $(document).ready(function() {
                            $("#datatable").DataTable({
                                data: content,
                                columns: [
                                    {data: null, render: function(data, type, row, meta) {
                                        return meta.row + 1;
                                    }
                                    },
                                    {
                                        data: "ts",
                                        render: function(data) {
                                            var date = new Date(data);
                                            return date.toISOString();
                                        },
                                        type: "date"
                                    },
                                    {data: "value"},
                                    {data: "AutoReg"},
                                    {data: "ExpSmoothing"}
                                ],
                                pageLength: 15,
                                lengthChange: false,
                                order: [[0]]
                            });
                        });
                    '''.replace(
                        'content', json.dumps(self.content)
                        )
                    
                    )