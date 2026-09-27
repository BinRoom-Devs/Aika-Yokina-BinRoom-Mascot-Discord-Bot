"""Berisi functions buat ngejaga rate limit."""

import time
from collections import deque

from ._config import (
    MENIT_RATE_LIMIT_REQ,
    PERKIRAAN_TOKEN_DEFAULT,
    RATE_LIMIT_HARIAN,
    RATE_LIMIT_TOKEN_PERHARI,
    RATE_LIMIT_TOKEN_PERMENIT,
)


class PembatasRate:
    def __init__(self):
        self.req_menit = deque()
        self.tok_menit = deque()
        self.total_tok_menit = 0
        
        self.req_harian = deque()
        self.tok_harian = deque()
        self.total_tok_harian = 0
    
    def hapus_catatan_usang(self, wkt_sekarang:float):
        while self.req_menit and wkt_sekarang - self.req_menit[0] > 60:
            self.req_menit.popleft()
        
        while self.tok_menit and wkt_sekarang - self.tok_menit[0][0] > 60:
            _, tok = self.tok_menit.popleft()
            self.total_tok_menit -= tok
        
        while self.req_harian and wkt_sekarang - self.req_harian[0] > 86400:
            self.req_harian.popleft()
        while self.tok_harian and wkt_sekarang - self.tok_harian[0][0] > 86400:
            _, tok = self.tok_harian.popleft()
            self.total_tok_harian -= tok
        
        self.total_tok_menit = max(self.total_tok_menit, 0)
        self.total_tok_harian = max(self.total_tok_harian, 0)
    
    def cek_batas(self, perkiraan_token:int=PERKIRAAN_TOKEN_DEFAULT) -> tuple[bool, str]:
        wkt_sekarang = time.time()
        self.hapus_catatan_usang(wkt_sekarang)
        
        if len(self.req_menit) >= MENIT_RATE_LIMIT_REQ:
            return False, "Batas rate limit tercapai: Terlalu banyak request per menit. Coba lagi nanti."
        if len(self.req_harian) >= RATE_LIMIT_HARIAN:
            return False, "Kuota request harian hampir penuh. Coba lagi besok."
        if self.total_tok_menit + perkiraan_token > RATE_LIMIT_TOKEN_PERMENIT:
            return False, "Batas token tercapai: Terlalu banyak request per menit. Coba lagi nanti."
        if self.total_tok_harian + perkiraan_token > RATE_LIMIT_TOKEN_PERHARI:
            return False, "Batas token harian tercapai. Coba lagi besok."
        
        return True, ""
    
    def rekam_penggunaan(self, token_terpakai:int):
        wkt_sekarang = time.time()
        self.req_menit.append(wkt_sekarang)
        self.req_harian.append(wkt_sekarang)
        self.tok_menit.append((wkt_sekarang, token_terpakai))
        self.tok_harian.append((wkt_sekarang, token_terpakai))
        self.total_tok_menit += token_terpakai
        self.total_tok_harian += token_terpakai