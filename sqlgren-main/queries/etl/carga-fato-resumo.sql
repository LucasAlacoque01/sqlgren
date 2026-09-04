-- Resumo: Carga incremental do fato resumo diário de produção
INSERT INTO tb_fat_resumo_diario (
    co_dim_tempo,
    co_dim_unidade_saude,
    qt_atendimentos,
    qt_cidadaos,
    dt_carga
)
SELECT
    tdt.co_seq_dim_tempo,
    tdus.co_seq_dim_unidade_saude,
    COUNT(*) AS qt_atendimentos,
    COUNT(DISTINCT pr.co_fat_cidadao_pec) AS qt_cidadaos,
    CURRENT_DATE
FROM tb_fat_proced_atend_proced pr
JOIN tb_dim_tempo tdt ON pr.co_dim_tempo = tdt.co_seq_dim_tempo
JOIN tb_dim_unidade_saude tdus ON pr.co_dim_unidade_saude = tdus.co_seq_dim_unidade_saude
WHERE tdt.dt_registro = CURRENT_DATE - INTERVAL '1 day'
GROUP BY tdt.co_seq_dim_tempo, tdus.co_seq_dim_unidade_saude;
