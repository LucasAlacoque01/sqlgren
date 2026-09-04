-- Resumo: Marca mudança de território para cidadãos sem vínculo ativo
UPDATE tb_fat_cidadao_territorio
SET st_mudou_se = 1,
    dt_atualizacao = CURRENT_DATE
WHERE st_vivo = 1
  AND st_mudou_se = 0
  AND co_fat_cidadao_pec NOT IN (
      SELECT pec.co_seq_fat_cidadao_pec
      FROM tb_fat_cidadao_pec pec
      JOIN tb_cidadao_vinculacao_equipe cve ON pec.co_cidadao = cve.co_cidadao
      WHERE cve.st_ativo = 1
  );
