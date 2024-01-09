## How do I cite CaeNDR?

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

## What are hyper-divergent regions? How should I use variants that fall within these regions? 

Hyper-divergent regions are genomic intervals that contain sequences not found in the N2 reference strain. They were identified by high levels of variation and low coverage from read alignments. For a more full description, please read [this paper](https://andersenlab.org/publications/2021LeeNatureEE.pdf). We highly recommend that you use the genome browser and view the BAM files for strains of interest. We also released a genomic view track to see where we have classified divergent regions. If you find that your region of interest overlaps with a hyper-divergent region, then we recommend taking any variants as preliminary. Long-read sequencing is required to identify the actual genomic sequences in this region.

## How much confidence do we have in the indel variants?

GATK calls indel variants (1-50 bp) and short structural variants. The variant calling at these sites was not optimized and ran default parameters. These variants should be considered preliminary until confirmed by PCR or long-read sequencing.

## How were the filter thresholds determined?

Optimal filter thresholds would faithfully separate real variant sites from non-variant sites. However, we had no way to know which variant sites were true or false using the experimental data. Therefore, we created simulated data with a "truth set" of variants artificially inserted into a BAM file. In this way, we know precisely the positions of true variants. After variant calling with the simulated BAM file, we looked at the various quality metrics and asked what thresholds of these metrics would best separate real variants from incorrectly called variants. We chose filter thresholds to maximize true positive rate and precision while minimizing the false positive rate. These filter thresholds were used in processing the wild isolate data.

**[See our filter optimization report for further details]({{ ext_asset('data/20200803_optimization_report.html') }})**

### How are strains grouped by isotype?

In 2012, we [published](http://dx.doi.org/10.1038/ng.1050) genome-wide variant data from reduced representation sequencing of approximately 10% of the *C. elegans* genome (RAD-seq). Using these data, we grouped strains into isotypes. We also found many strains that were mislabeled as wild isolates but were instead N2 derivatives, recombinants from laboratory experiments, and mutagenesis screen isolates (detailed in [Strain Issues](/)). These strains were not characterized further. For the isotypes, we chose one strain to be the isotype reference strain. This strain can be ordered through CaeNDR [here]({{ url_for('request_strains.request_strains') }}).

After 2012, with advances in genome sequencing, we transitioned our sequencing to whole-genome short-read sequencing.
All isotype reference strains were resequenced whole-genome.  The other strains within an isotype were not,
so we use the RAD-seq variant data to group isotypes for these strains.
