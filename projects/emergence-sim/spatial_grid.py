#!/usr/bin/env python3
"""
Spatial hash grid for O(1) neighbor lookups in the emergence sim.

Replaces O(n²) all-pairs distance checks with grid-based spatial indexing.
Each cell is `cell_size` units wide. To find neighbors within radius R,
we only check cells within ceil(R/cell_size) of the query cell.

Handles toroidal wrapping (the sim world wraps in both X and Y).
"""

import math


class SpatialGrid:
    """Grid-based spatial index for fast neighbor queries on a toroidal world."""

    __slots__ = ('cell_size', 'width', 'height', 'cols', 'rows', 'grid')

    def __init__(self, width: float, height: float, cell_size: float = 12.0):
        self.cell_size = cell_size
        self.width = width
        self.height = height
        self.cols = max(1, int(math.ceil(width / cell_size)))
        self.rows = max(1, int(math.ceil(height / cell_size)))
        self.grid = {}

    def _cell(self, x: float, y: float) -> tuple:
        """Get grid cell coordinates for a position."""
        cx = int(x / self.cell_size) % self.cols
        cy = int(y / self.cell_size) % self.rows
        return (cx, cy)

    def clear(self):
        """Remove all entities from the grid."""
        self.grid.clear()

    def insert(self, entity):
        """Insert an entity (must have .x and .y attributes)."""
        cell = self._cell(entity.x, entity.y)
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append(entity)

    def rebuild(self, entities):
        """Clear and re-insert all entities. Call once per tick."""
        self.grid.clear()
        for e in entities:
            cell = self._cell(e.x, e.y)
            if cell not in self.grid:
                self.grid[cell] = []
            self.grid[cell].append(e)

    def query_radius(self, x: float, y: float, radius: float):
        """Yield all entities within `radius` of (x, y), with toroidal wrapping.
        
        Returns (entity, distance) pairs. Does NOT filter out the query entity itself.
        """
        r_cells = int(math.ceil(radius / self.cell_size))
        cx, cy = self._cell(x, y)
        r_sq = radius * radius
        w = self.width
        h = self.height
        half_w = w / 2
        half_h = h / 2

        for dcx in range(-r_cells, r_cells + 1):
            for dcy in range(-r_cells, r_cells + 1):
                ncx = (cx + dcx) % self.cols
                ncy = (cy + dcy) % self.rows
                cell = (ncx, ncy)
                if cell not in self.grid:
                    continue
                for entity in self.grid[cell]:
                    dx = abs(entity.x - x)
                    if dx > half_w:
                        dx = w - dx
                    dy = abs(entity.y - y)
                    if dy > half_h:
                        dy = h - dy
                    d_sq = dx * dx + dy * dy
                    if d_sq <= r_sq:
                        yield entity, math.sqrt(d_sq)

    def neighbors(self, entity, radius: float, exclude_self: bool = True):
        """Get all neighbors of an entity within radius.
        
        Returns list of (other_entity, distance) pairs.
        """
        results = []
        for other, dist in self.query_radius(entity.x, entity.y, radius):
            if exclude_self and other is entity:
                continue
            results.append((other, dist))
        return results
