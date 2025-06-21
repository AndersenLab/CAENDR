1. [How do I cite CaeNDR?](#cite)
2. [What are hyper-divergent regions? How should I use variants that fall within these regions?](#hdrs)
3. [Does CaeNDR have API access for computationally efficient data downloads?](#api)
4. [How much confidence do we have in the indel variants?](#indel)
5. [How were the filter thresholds determined?](#filter-thresholds)
6. [What strains and data are available from CaeNDR?](#strain-availability)
7. [How are strains grouped by isotype?](#isotypes)
8. [What are the differences in each tool? Why do some tools annotate variants and others don’t?](#tool-differences)
9. [What are compound variant annotations by CSQ?](#csq)
10. [What are Grantham scores?](#grantham)
11. [What are BLOSUM62 scores?](#blosum)
12. [What is the percent protein metric?](#percent-protein)
13. [What is the divergent column?](#divergent-column)
14. [How does CaeNDR decide on pricing?](#pricing)

## <a id="cite"></a>How do I cite CaeNDR?

Please use the citation below.

<div class="card mb-3">
  <div class="row g-2">
    <div class="col-md-4">
      <a href="https://andersenlab.org/publications/2016CookOxford.pdf" target="_blank">
            <img class="d-block img-fluid rounded mx-auto" src="{{ ext_asset('img/2016CookOxford.thumb.png') }}" alt="">
            </a>
    </div>
    <div class="col-md-8 ps-3">
      <div class="card-body">
        <h3 class="h5 card-title">CaeNDR, the <em>Caenorhabditis</em> Natural Diversity Resource</h3>
        <p class="card-text">
          {% include "_includes/cite-caendr.html" %}
        </p>
      </div>
    </div>
  </div>
</div>
Or use this bibtex entry
<pre><code>
{% include "_includes/cite-caendr.bibtex" %}
</code></pre>

## <a id="hdrs"></a>What are hyper-divergent regions? How should I use variants that fall within these regions? 

Hyper-divergent regions are genomic intervals that contain sequences not found in the N2 reference strain. They were identified by high levels of variation and low coverage from read alignments. For a more full description, please read [this paper](https://andersenlab.org/publications/2021LeeNatureEE.pdf). We highly recommend that you use the genome browser and view the BAM files for strains of interest. We also released a genomic view track to see where we have classified hyper-divergent regions. If you find that your region of interest overlaps with a hyper-divergent region, then we recommend taking any variants as preliminary. Long-read sequencing is required to identify the actual genomic sequences in this region.


## <a id="api"></a>Does CaeNDR have API access for computationally efficient data downloads?

Amazon Web Services (AWS) Open Data Project is making the CaeNDR data publicly available to the community free of charge. Public Data Sets on AWS provide a centralized repository of public data hosted on Amazon Simple Storage Service (Amazon S3). The data can be seamlessly accessed from AWS services such Amazon Elastic Compute Cloud (Amazon EC2) and Amazon Elastic MapReduce (Amazon EMR), which provide organizations with the highly scalable compute resources needed to take advantage of these large data collections. Researchers pay only for the additional AWS resources they need for further processing or analysis of the data. Learn more about [Public Data Sets on AWS](https://aws.amazon.com/publicdatasets/).

The latest CaeNDR Project data is publicly available in the [CaeNDR Amazon S3 bucket](http://s3.amazonaws.com/caendr).

We are working to implement an API to provide even more seamless data downloads.


## <a id="indel"></a>How much confidence do we have in the indel variants?

GATK calls indel variants (1-50 bp) and short structural variants. The variant calling at these sites was not optimized and ran default parameters. These variants should be considered preliminary until confirmed by PCR or long-read sequencing.

## <a id="filter-thresholds"></a>How were the filter thresholds determined?

Optimal filter thresholds would faithfully separate real variant sites from non-variant sites. However, we had no way to know which variant sites were true or false using the experimental data. Therefore, we created simulated data with a "truth set" of variants artificially inserted into a BAM file. In this way, we know precisely the positions of true variants. After variant calling with the simulated BAM file, we looked at the various quality metrics and asked what thresholds of these metrics would best separate real variants from incorrectly called variants. We chose filter thresholds to maximize true positive rate and precision while minimizing the false positive rate. These filter thresholds were used in processing the wild isolate data.

**[See our filter optimization report for further details]({{ ext_asset('data/20200803_optimization_report.html') }})**

### <a id="strain-availability"></a>What strains and data are available from CaeNDR?

The strains available on CaeNDR were sampled from all over the world by many members of the *Caenorhabditis* research community. CaeNDR endeavors to cryopreserve and whole-genome sequence all wild strains from *C. briggsae*, *C. elegans*, and *C. tropicalis* from all unique worldwide collection locations. Most times, independent strains collected from the same natural substrate are very genetically similar (or identical to the best level of determination by Illumina short-read sequencing SNV calling). Additionally, independent strains collected from nearby locations are often similar or identical. Because use of these strains in measurements of natural phenotypic diversity and in genome-wide association studies will cause significant bias, CaeNDR classifies strains that share high levels of genetic diversity as isotypes using whole-genome sequencing and variant calling. To remove this bias, we suggest one strain in each isotype, called the isotype reference strain. Strains and data on CaeNDR are focused on isotype reference strains. Users can request strains from the lab who originally identified the wild strains, but these strains are not genome-sequence verified and data on CaeNDR might not match strains from individual labs.

### <a id="isotypes"></a>How are strains grouped by isotype?

In 2012, we [published](http://dx.doi.org/10.1038/ng.1050) genome-wide variant data from reduced representation sequencing of approximately 10% of the *C. elegans* genome (RAD-seq). Using these data, we grouped strains into isotypes. We also found many strains that were mislabeled as wild isolates but were instead N2 derivatives, recombinants from laboratory experiments, and mutagenesis screen isolates (detailed in [Strain Issues]({{ url_for('request_strains.strains_issues') }})). These strains were not characterized further. For the isotypes, we chose one strain to be the isotype reference strain. This strain can be ordered through CaeNDR [here]({{ url_for('request_strains.request_strains') }}).

After 2012, with advances in genome sequencing, we transitioned our sequencing to whole-genome short-read sequencing.
All isotype reference strains were resequenced whole-genome.  The other strains within an isotype were not,
so we use the RAD-seq variant data to group isotypes for these strains.

### <a id="tool-differences"></a>What are the differences in each tool? Why do some tools annotate variants and others don’t?

Annotations were obtained from ANNOVAR and VEP using default parameter settings. This includes annotating variants that are 5kb upstream or downstream of a transcript for VEP, described <a href="https://www.ensembl.org/info/docs/tools/vep/script/VEP_script_documentation.pdf">here</a>, and 1kb for ANNOVAR, described <a href="https://academic.oup.com/nar/article/38/16/e164/1749458">here</a>, using their gene-based annotation mode. These parameters result in ANNOVAR and VEP annotating variants that fall in intergenic regions in addition to coding and regulatory regions.

VEP returns a qualitative impact score in addition to a predicted consequence. These impacts are HIGH, MODERATE, LOW, or MODIFIER based on the predicted consequence and if it is likely to disrupt protein function. For example, a stop_gained annotation would have an impact of HIGH, while a synonymous_variant annotation would have an impact of LOW.

ANNOVAR returns two consequence annotations, one that specifies where in a transcript a variant falls (exonic, splicing, UTR5, downstream, etc), and another that species the type of consequence that is predicted in that region (stoploss, nonsynonymous_SNV, frameshift_deletion, etc).

CSQ is haplotype aware and does annotate intergenic variants. VEP and ANNOVAR may annotate variants in coding regions that CSQ does not annotate. This discrepancy in annotation is because of CSQ’s haplotype-aware functionality. If there is a deletion spanning five base pairs at position 100 on chromosome I, and then a single-nucleotide variant call at position 103 on chromosome I, CSQ will not annotate the variant at position 103 because it conflicts with the variant at position 100 and it cannot resolve the haplotype.

Some annotations from CSQ will have an asterisk (*) before the predicted consequence. This asterisk indicates that the predicted consequence is downstream from a predicted nonsense (early stop) variant.

SnpEff is used for annotating MtDNA variants because it allows for the user to specify an MtDNA codon table, described <a href="https://www.tandfonline.com/doi/full/10.4161/fly.19695#d1e229">here</a>. For annotating MtDNA variants in Caenorhabditis, codon table 5 (invertebrate) is used. 

### <a id="csq"></a>What are compound variant annotations by CSQ?

Bcftools’s variant annotation tool CSQ makes haplotype aware variant annotations. Meaning, if two or more variants are in the same haplotype and are observed in the same sample, then the combination of their effect may have a different consequence than the effects each individual variant would have. The creators provide some examples of these compound effects in their paper linked here.

An example of how a compound variant is reported is displayed here:

>III,2371323,C,T,@2371328,@2371328,@2371328,<strains>,NO,@2371328,@2371328,@2371328,N/A,N/A,N/A
>III,2371325,ATG,A,@2371328,@2371328,@2371328,<strains>,NO,@2371328,@2371328,@2371328,N/A,N/A,N/A

The variants at position 2371323 and 2371325 are in the same haplotype as the variant at position 2371328, and together, they have a predicted consequence that is reported on the line where the 2371328 variant is reported and where the DNA change column is the ref>alt (@2371323) + ref>alt (@2371325) + ref>alt (@2371328):

>III,2371328,C,CTA,stop_gained&inframe_altering,146AL>146*,2371323C>T+2371325ATG>A+2371328C>CTA,<strains>,NO,H04J21.1.1,WBGene00019150,N/A,N/A,N/A,20.82

The reason CSQ annotations have a “DNA change” column but annotations from other tools do not is in order to differentiate predicted consequences that are from a compound annotation versus an individual variant annotation.

### <a id="grantham"></a>What are Grantham scores? 

Grantham scores are a quantitative measure of how different an amino acid is from another based on combining properties of composition, polarity, and molecular volume and range from 5 to 215, described <a href="https://www.science.org/doi/10.1126/science.185.4154.862">here</a>. Amino acid pairs that have a high Grantham score are predicted to be more deleterious than amino acid pairs with a lower Grantham score. The grantham matrix used for scoring can be seen here:

<div class="card mb-3">
<img class="d-block img-fluid rounded mx-auto" src="{{ ext_asset('img/help/grantham.png') }}" alt="Grantham Amino Acid Substitution Table">
</div>

### <a id="blosum"></a>What are BLOSUM62 scores?

BLOSUM62 (BLOcks SUbstitution Matrix) scores represent the log-odds of observing a given amino acid substitution (REF → ALT) compared to what would be expected by chance. Positive scores indicate amino acid substitution that are observed more frequently in evolutionarily related protein sequences, while negative scores indicate rare substitutions that may be deleterious to protein function. The BLOSUM62 matrix was derived from roughly 2,000 conserved regions ("blocks") across over 500 families of related proteins that share at least 62% sequence identity, decribed <a href="https://www.pnas.org/doi/epdf/10.1073/pnas.89.22.10915">here</a>. SnpEff does not have BLOSUM62 scores because the BLOSU62 matrix was created based on nuclear proteins.

<div class="card mb-3">
<img class="d-block img-fluid rounded mx-auto" src="{{ ext_asset('img/help/blosum.png') }}" alt="BLOSUM62 Amino Acid Substitution Table">
</div>

### <a id="percent-protein"></a>What is the percent protein metric?

The percent protein metric is a calculation of where in the protein a variant is present. The percent protein is calculated based on the nucleotide position of a variant in relation to the entire coding sequence, and accounts for Watson-Crick strandedness. All the coding regions for a transcript are summed, then the difference in the nucleotide position of a variant in relation to the position of where the first coding region begins is calculated and then divided by the total number of nucleotides in the coding region for a transcript. 

### <a id="divergent-column"></a>What is the divergent column?

Previous studies in the Andersen Laboratory have identified punctuated genomic regions that have extreme genetic variation in selfing Caenorhabditis species. These regions are referred to as hyper-divergent regions (HDRs). To learn more, please read this <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC8202730/">paper</a>. HDRs are different for each wild strain, therefore, we have added resolution on if a variant call falls in a HDR for a given wild strain. If the divergent column has a value of YES, this indicates that the variation position is in a HDR for the strains that have the alt allele. Inversely, if the divergent column has a value of NO, this indicates that the variant position is not in a HDR for the strains that have the alt allele. Given the extreme genomic divergence in HDRs, we recommend taking variant calls in HDRs as preliminary, as it is necessary to have long-read sequencing to identify the actual genomic sequences in these regions.

### <a id="pricing"></a>How does CaeNDR decide on pricing?

Prices for individual strains, diversity sets, and larger strain panels reflect the costs of strain cryopreservation, whole-genome sequencing, compute costs for data processing, web hosting costs, and data storage. Increases are evaluated every three years in response to these costs in consultation with members of the Advisory Committee. 