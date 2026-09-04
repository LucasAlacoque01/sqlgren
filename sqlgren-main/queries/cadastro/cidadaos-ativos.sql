-- Resumo: Cidadãos ativos no território com vínculo de equipe
SELECT
    pec.no_cidadao,
    pec.nu_cns,
    pec.nu_cpf_cidadao,
    ds.ds_sexo,
    tdus.no_unidade_saude,
    tde.no_equipe,
    fct.st_vivo
FROM tb_fat_cidadao_pec pec
JOIN tb_fat_cidadao_territorio fct
    ON pec.co_seq_fat_cidadao_pec = fct.co_fat_cidadao_pec
JOIN tb_cidadao_vinculacao_equipe cve
    ON pec.co_cidadao = cve.co_cidadao
JOIN tb_dim_unidade_saude tdus
    ON cve.nu_cnes = tdus.nu_cnes
JOIN tb_dim_equipe tde
    ON cve.nu_ine = tde.nu_ine
JOIN tb_dim_sexo ds
    ON pec.co_dim_sexo = ds.co_seq_dim_sexo
WHERE fct.st_vivo = 1
  AND fct.st_mudou_se = 0
ORDER BY tdus.no_unidade_saude, pec.no_cidadao
LIMIT :limite;
