from fasthtml.common import *
from dataclasses import dataclass
import json

@dataclass
class Card:
    name: str
    error: float
    
    def __ft__(self):
        return Div(
                    Div(
                        H2(self.name, cls='card-title'),
                        Div(
                            Div(
                                Div('RMSE', cls='stat-title text-slate-600'),
                                Div(f'{self.error:.1f}', cls='stat-value text-primary'),
                                cls='stat'
                            ),
                            cls='grid grid-cols-2 gap-4'
                        ),
                        cls='card-body'
                    ),
                    cls='card w-96 bg-white shadow-md'
                )