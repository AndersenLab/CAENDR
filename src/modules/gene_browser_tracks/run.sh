#!/bin/bash
# Author: Daniel E. Cook
# This script generates the transcript and gene track for the browser.

function zip_index {
    bgzip -f ${1}
    tabix ${1}.gz
}
# Generate the transcripts track;
# Confusingly, this track is derived from 
# one called elegans_genes on wormbase.
# Add parenthetical gene name for transcripts.
mkdir -p browser

set -o allexport
source .env
set +o allexport

curl ${GENE_BB_URL} >> elegans_genes_${WORMBASE_VERSION}.bb
curl ${GENE_GFF_URL} >> c_elegans.PRJNA13758.${WORMBASE_VERSION}.annotations.gff3.gz

bigBedToBed elegans_genes_${WORMBASE_VERSION}.bb tmp.bed
sortBed -i tmp.bed > browser/elegans_transcripts_${WORMBASE_VERSION}.bed
bgzip -f browser/elegans_transcripts_${WORMBASE_VERSION}.bed
tabix browser/elegans_transcripts_${WORMBASE_VERSION}.bed.gz
rm tmp.bed

# Generate Gene Track BED File
tmp_gff=$(mktemp)
tmp_gff2=$(mktemp)
tmp_bed3=$(mktemp)
gzip -dc c_elegans.PRJNA13758.${WORMBASE_VERSION}.annotations.gff3.gz | \
grep 'locus' | \
awk '$2 == "WormBase" && $3 == "gene"' > "${tmp_gff}"
sortBed -i "${tmp_gff}" > "${tmp_gff2}"
# Install with conda install gawk
convert2bed -i gff < "${tmp_gff2}" > ${tmp_bed3}
gawk -v OFS='\t' '{ match($0, "locus=([^;\t]+)", f); $4=f[1]; print $1, $2, $3, $4, 100, $6  }' "${tmp_bed3}" | \
uniq > browser/elegans_gene.${WORMBASE_VERSION}.bed
zip_index browser/elegans_gene.${WORMBASE_VERSION}.bed

# Copy tracks to browser
gsutil cp browser/* gs://${MODULE_SITE_BUCKET_PUBLIC_NAME}/${MODULE_GENE_BROWSER_TRACKS_PATH}/${WORMBASE_VERSION}

