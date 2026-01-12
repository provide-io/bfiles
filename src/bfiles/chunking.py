#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""File chunking with token-based splitting and overlap."""

from pathlib import Path

import attrs
from provide.foundation import logger
import tiktoken

from bfiles.config import BfilesConfig
from bfiles.errors import ChunkingError, TokenizationError


@attrs.define
class ChunkData:
    """Data for a single chunk."""

    chunk_num: int
    total_chunks: int
    tokens: list[int]
    token_count: int
    overlap_bytes_prev: int | None = None


class FileChunker:
    """Chunks files based on token count with configurable overlap."""

    def __init__(self, config: BfilesConfig) -> None:
        self.config = config
        self._encoder: tiktoken.Encoding | None = None

    def should_chunk(self, content: str | None, token_count: int | None, had_encoding_error: bool) -> bool:
        """Determine if file should be chunked.

        Args:
            content: File content
            token_count: Total token count for file
            had_encoding_error: Whether encoding errors occurred

        Returns:
            True if file should be chunked
        """
        if self.config.chunk_size is None:
            return False

        if content is None or had_encoding_error:
            return False

        return not (token_count is None or token_count <= self.config.chunk_size)

    def chunk(self, content: str, file_path: Path) -> list[ChunkData]:
        """Chunk file content into token-based chunks with overlap.

        Args:
            content: File content to chunk
            file_path: Path for logging

        Returns:
            List of ChunkData objects

        Raises:
            ChunkingError: If chunking fails
        """
        if self.config.chunk_size is None:
            raise ChunkingError("chunk_size not configured")

        logger.info(
            "file.chunk.start",
            path=str(file_path),
            chunk_size=self.config.chunk_size,
            overlap=self.config.chunk_overlap,
        )

        try:
            encoder = self._get_encoder()
            tokens = encoder.encode(content)
        except Exception as e:
            raise TokenizationError(f"Failed to tokenize {file_path}: {e}") from e

        chunks = self._split_tokens(tokens)

        if not chunks:
            logger.warning("file.chunk.no_chunks", path=str(file_path))
            raise ChunkingError(f"Chunking {file_path} resulted in no chunks")

        chunk_data_list = self._create_chunk_data(chunks, encoder)

        logger.info(
            "file.chunk.complete",
            path=str(file_path),
            chunk_count=len(chunk_data_list),
        )

        return chunk_data_list

    def _get_encoder(self) -> tiktoken.Encoding:
        """Get or create tiktoken encoder.

        Returns:
            Tiktoken encoder

        Raises:
            TokenizationError: If encoder creation fails
        """
        if self._encoder is None:
            try:
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                raise TokenizationError(f"Failed to get tiktoken encoder: {e}") from e

        return self._encoder

    def _split_tokens(self, tokens: list[int]) -> list[list[int]]:
        """Split tokens into chunks with overlap.

        Args:
            tokens: List of all tokens

        Returns:
            List of token lists (chunks)
        """
        if self.config.chunk_size is None:
            return []

        chunks: list[list[int]] = []
        current_pos = 0

        while current_pos < len(tokens):
            start_pos = current_pos
            end_pos = min(current_pos + self.config.chunk_size, len(tokens))
            chunks.append(tokens[start_pos:end_pos])

            current_pos += self.config.chunk_size

            if current_pos < len(tokens) and self.config.chunk_overlap > 0:
                current_pos -= self.config.chunk_overlap

        return chunks

    def _create_chunk_data(self, chunks: list[list[int]], encoder: tiktoken.Encoding) -> list[ChunkData]:
        """Create ChunkData objects with overlap calculations.

        Args:
            chunks: List of token chunks
            encoder: Tiktoken encoder for decoding

        Returns:
            List of ChunkData objects
        """
        total_chunks = len(chunks)
        chunk_data_list: list[ChunkData] = []
        previous_chunk_tokens: list[int] | None = None

        for i, current_chunk_tokens in enumerate(chunks):
            chunk_num = i + 1
            overlap_bytes = None

            if chunk_num > 1 and self.config.chunk_overlap > 0 and previous_chunk_tokens:
                overlap_bytes = self._calculate_overlap_bytes(current_chunk_tokens, encoder, chunk_num)

            chunk_data = ChunkData(
                chunk_num=chunk_num,
                total_chunks=total_chunks,
                tokens=current_chunk_tokens,
                token_count=len(current_chunk_tokens),
                overlap_bytes_prev=overlap_bytes,
            )

            chunk_data_list.append(chunk_data)
            previous_chunk_tokens = current_chunk_tokens

        return chunk_data_list

    def _calculate_overlap_bytes(
        self, current_chunk_tokens: list[int], encoder: tiktoken.Encoding, chunk_num: int
    ) -> int | None:
        """Calculate byte size of overlap with previous chunk.

        Args:
            current_chunk_tokens: Tokens for current chunk
            encoder: Tiktoken encoder
            chunk_num: Current chunk number for logging

        Returns:
            Overlap byte count or None if calculation fails
        """
        if len(current_chunk_tokens) < self.config.chunk_overlap:
            logger.warning(
                "file.chunk.overlap_too_short",
                chunk_num=chunk_num,
                chunk_token_count=len(current_chunk_tokens),
                overlap=self.config.chunk_overlap,
            )
            return None

        try:
            overlapping_tokens = current_chunk_tokens[: self.config.chunk_overlap]
            overlap_content = encoder.decode(overlapping_tokens)
            overlap_bytes = len(overlap_content.encode(self.config.encoding, errors="replace"))
        except Exception as e:
            logger.warning(
                "file.chunk.overlap_decode_error",
                chunk_num=chunk_num,
                error=str(e),
            )
            return None
        else:
            return overlap_bytes


# 🐝📁🔚
