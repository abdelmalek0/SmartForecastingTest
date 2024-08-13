from fasthtml.common import *
from dataclasses import dataclass

@dataclass
class DateFilter:
    start_date: str
    end_date: str
    min_date: str
    max_date: str

    def create_input(self, name: str, value: str, placeholder: str) -> Input:
        """Helper method to create an input field with common styling."""
        return Input(
            id=name,
            name=name,
            value=value,
            placeholder=placeholder,
            cls='input input-bordered join-item bg-white w-[250px] date'
        )

    def __ft__(self) -> Form:
        """Create a form for filtering dates."""
        return Form(
            Script('''
                   $(document).ready(function() {
                        $(".date").flatpickr({
                            enableTime: true,
                            dateFormat: "Z",
                            altInput: true,
                            altFormat: "Z",
                            utc: true, // This ensures UTC time is used
                            time_24hr: true, // Use 24-hour format
                            minDate: "MAX_PLACEHOLDER",  
                            maxDate: "MIN_PLACEHOLDER",
                        })
                   });
                   '''.replace('MIN_PLACEHOLDER', self.min_date).replace(
                       'MAX_PLACEHOLDER', self.max_date)
                   ),
            Style('''
                  .flatpickr-calendar {
                      height: 0px;
                  }
                  '''),
            Div(
                self.create_input("start_date", self.start_date, "Start Date"),
                cls='form-control',
                
            ),
            Div(
                self.create_input("end_date", self.end_date, "End Date"),
                cls='form-control'
            ),
            Div(
                Button(
                    'Filter', 
                    type='submit', 
                    cls='btn join-item btn-primary text-slate-100'
                ),
                cls='indicator'
            ),
            cls='flex flex-row items-center justify-end join'
        )
