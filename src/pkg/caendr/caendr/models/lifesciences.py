class Disk(object):
  def __init__(self, name=None, size_gb=None, type=None, source_image=None):
    self.name = name                  # String
    self.sizeGb = size_gb             # Integer
    self.type = type                  # String
    self.sourceImage = source_image   # String

class PersistentDisk(object):
  def __init__(self, size_gb=None, type=None, source_image=None):
    self.sizeGb = size_gb               # Integer
    self.type = type                    # String
    self.sourceImage = source_image     # String

class ExistingDisk(object):
  def __init__(self, disk=None):
    self.disk = disk    # String

class NFSMount(object):
    def __init__(self, target=None):
      self.target = target    # String

class Volume(object):
  def __init__(self, volume=None, persistent_disk=None, existing_disk=None, nfs_mount=None):
    self.volume = volume,                     # String
    self.persistentDisk = persistent_disk     # { Object (PersistentDisk) }
    self.existingDisk = existing_disk         # { Object (ExistingDisk) }
    self.nfsMount = nfs_mount                 # { Object (NFSMount) }

class Mount(object):
  def __init__(self, disk=None, path=None, read_only=None):
    self.disk = disk                  # String
    self.path = path                  # String
    self.readOnly = read_only         # Boolean

class ServiceAccount(object):
  def __init__(self, email=None, scopes=None):
    self.email = email          # String
    self.scopes = scopes        # [ String, ... ]

class Network(object):
  def __init__(self, network=None, use_private_address=None, subnetwork=None):
    self.network = network                          # String
    self.usePrivateAddress = use_private_address    # Boolean
    self.subnetwork = subnetwork                    # String

class VirtualMachine(object):
  def __init__(self, machine_type=None, preemptible=None, labels=None, disks=None, network=None, accelerators=None, service_account=None, 
               boot_disk_size_gb=None, cpu_platform=None, boot_image=None, nvidia_diver_version=None, enable_stackdriver_monitoring=None, 
               docker_cache_images=None, volumes=None, reservation=None):
    self.machineType = machine_type                     # String
    self.preemptible = preemptible                      # Boolean
    self.labels = labels                                # {String: String, ...}
    self.disks = disks                                  # Object (Disk)
    # self.network = network,                             # Object (Network)
    self.accelerators = accelerators                    # [ { Object (Accelerator) }, ...]
    self.serviceAccount = service_account               # Object (ServiceAccount)
    self.bootDiskSizeGb = boot_disk_size_gb             # Integer
    self.cpuPlatform = cpu_platform                     # String
    self.bootImage = boot_image                         # String
    self.nvidiaDriverVersion = nvidia_diver_version     # String
    self.enableStackdriverMonitoring = enable_stackdriver_monitoring    # Boolean
    self.dockerCacheImages = docker_cache_images        # [ String, ... ]
    self.volumes = volumes                              # [ { Object (Volume) }, ... ]
    self.reservation = reservation                      # String

class Resources(object):
  def __init__(self, regions=None, zones=None, virtual_machine=None):
    self.regions = regions                  # [ String, ... ]
    self.zones = zones                      # [ String, ... ]
    self.virtualMachine = virtual_machine   # { Object (VirtualMachine) }

class Action(object):
  def __init__(self, container_name=None, image_uri=None, commands=None, entrypoint=None, environment=None, 
               encrypted_environment=None, pid_namespace=None, port_mappings=None, mounts=None, labels=None, 
               credentials=None, timeout=None, ignore_exit_status=None, run_in_background=None, always_run=None, 
               enable_fuse=None, publish_exposed_ports=None, disable_image_prefetch=None, 
               disable_standard_error_capture=None, block_external_network=None):
    self.containerName = container_name                   # String
    self.imageUri = image_uri                             # String
    self.commands = commands                              # [ String, ... ]
    self.entrypoint = entrypoint                          # String
    self.environment = environment                        # { String: String, ... }
    self.encryptedEnvironment = encrypted_environment     # { Object (Secret) }
    self.pidNamespace = pid_namespace                 # String
    self.portMappings = port_mappings                 # { Integer: Integer, ... }
    self.mounts = mounts                              #  [ { Object (Mount) }, ... ]
    self.labels = labels                              # { String: String, ... }
    self.credentials = credentials                    # { Object (Secret) }
    self.timeout = timeout                            # String
    self.ignoreExitStatus = ignore_exit_status                              # Boolean
    self.runInBackground = run_in_background                                # Boolean
    self.alwaysRun = always_run                                             # Boolean
    self.enableFuse = enable_fuse                                           # Boolean
    self.publishExposedPorts = publish_exposed_ports                        # Boolean
    self.disableImagePrefetch = disable_image_prefetch                      # Boolean
    self.disableStandardErrorCapture = disable_standard_error_capture       # Boolean
    self.blockExternalNetwork = block_external_network                      # Boolean
  
class Pipeline(object):
  def __init__(self, actions=None, resources=None, timeout=None):
    self.actions = actions      # [ { Object (Action) }, ... ]
    self.resources = resources  # { Object (Resources) }
    self.timeout = timeout

class Request(object):
  def __init__(self, pipeline=None, labels=None, pub_sub_topic=None):
    self.pipeline = pipeline                # { Object (Pipeline) }
    self.labels = labels                    # { String: String, ... }
    self.pubSubTopic = pub_sub_topic        # String
  
