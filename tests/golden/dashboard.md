---
tipo: dashboard
tags: [sistema]
---

# 🏠 Dashboard — abre SIEMPRE esta nota primero

> [!tip] Regla de oro
> No decidas qué estudiar. El dashboard decide por ti. Tú solo ejecutas
> el primer elemento de la lista que coincida con tu energía actual.

## ⚡ ¿Cuánta energía tienes AHORA MISMO?

### 🔋 Poca (cansancio, medicación en valle, tarde-noche) → #baja-energia
```dataview
TASK
FROM #baja-energia
WHERE !completed
LIMIT 3
```

### 🔋🔋🔋 Normal o alta → #alta-energia
```dataview
TASK
FROM #alta-energia
WHERE !completed
LIMIT 3
```

## ⏳ Repasos que vencen (hazlos ANTES de material nuevo)
```dataview
TABLE fuente, proximo_repaso AS "vence"
FROM #repaso-48h OR "05 - Repaso espaciado"
WHERE proximo_repaso != "" AND date(proximo_repaso) <= date(today)
SORT proximo_repaso ASC
LIMIT 5
```

## 📊 Progreso visible (dopamina de datos)
```dataview
TABLE length(rows) AS "bloques completados"
FROM "02 - Derecho" OR "03 - Historia"
WHERE estado = "completado"
GROUP BY fuente
```

## 🚦 Bloques pendientes por capítulo
```dataview
TABLE bloque + "/" + total_bloques AS "avance", minutos AS "min"
FROM #bloque-20min
WHERE estado = "pendiente"
SORT fuente ASC, bloque ASC
LIMIT 8
```

---
*Sistema de 15 min/bloque, máx 4 bloques por sesión. Reglas completas: [[📜 Reglas del sistema]]*
