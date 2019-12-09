from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class AmisResponse(BaseResponse):
    def create_image(self):
        name = self.querystring.get("Name")[0]
        description = self._get_param("Description", if_none="")
        instance_id = self._get_param("InstanceId")
        if self.is_not_dryrun("CreateImage"):
            block_devices = []
            instance = self.ec2_backend.get_instance(instance_id)
            volume = self.ec2_backend.get_volume(instance.block_device_mapping['/dev/sda1'].volume_id)
            for device in self._get_list_prefix('BlockDeviceMapping'):
                volume_type = volume.volume_type if device['device_name'] == '/dev/sda1' else 'standard'
                volume_size = volume.size if device['device_name'] == '/dev/sda1' else 8
                storage = {
                    'device_name': device['device_name'],
                    'virtual_name': device.get('virtual_name'),
                    'ebs': {
                        'delete': device.get('ebs._delete_on_termination', True),
                        'iops': device.get('ebs._iops', None),
                        'volume_type': device.get('ebs._volume_type', volume_type),
                        'volume_size': device.get('ebs._volume_size', volume_size),
                        'volume_id': None
                    }
                 }
                block_devices.append(storage)
            image = self.ec2_backend.create_image(
                instance_id, name, description, block_device_mapping=block_devices, context=self
            )
            template = self.response_template(CREATE_IMAGE_RESPONSE)
            return template.render(image=image)

    def copy_image(self):
        source_image_id = self._get_param("SourceImageId")
        source_region = self._get_param("SourceRegion")
        name = self._get_param("Name")
        description = self._get_param("Description")
        if self.is_not_dryrun("CopyImage"):
            image = self.ec2_backend.copy_image(
                source_image_id, source_region, name, description
            )
            template = self.response_template(COPY_IMAGE_RESPONSE)
            return template.render(image=image)

    def deregister_image(self):
        ami_id = self._get_param("ImageId")
        if self.is_not_dryrun("DeregisterImage"):
            success = self.ec2_backend.deregister_image(ami_id)
            template = self.response_template(DEREGISTER_IMAGE_RESPONSE)
            return template.render(success=str(success).lower())

    def describe_images(self):
        ami_ids = self._get_multi_param("ImageId")
        filters = filters_from_querystring(self.querystring)
        owners = self._get_multi_param("Owner")
        exec_users = self._get_multi_param("ExecutableBy")
        images = self.ec2_backend.describe_images(
            ami_ids=ami_ids,
            filters=filters,
            exec_users=exec_users,
            owners=owners,
            context=self,
        )
        template = self.response_template(DESCRIBE_IMAGES_RESPONSE)
        return template.render(images=images)

    def describe_image_attribute(self):
        ami_id = self._get_param("ImageId")
        groups = self.ec2_backend.get_launch_permission_groups(ami_id)
        users = self.ec2_backend.get_launch_permission_users(ami_id)
        template = self.response_template(DESCRIBE_IMAGE_ATTRIBUTES_RESPONSE)
        return template.render(ami_id=ami_id, groups=groups, users=users)

    def modify_image_attribute(self):
        ami_id = self._get_param("ImageId")
        operation_type = self._get_param("OperationType")
        group = self._get_param("UserGroup.1")
        user_ids = self._get_multi_param("UserId")
        if self.is_not_dryrun("ModifyImageAttribute"):
            if operation_type == "add":
                self.ec2_backend.add_launch_permission(
                    ami_id, user_ids=user_ids, group=group
                )
            elif operation_type == "remove":
                self.ec2_backend.remove_launch_permission(
                    ami_id, user_ids=user_ids, group=group
                )
            return MODIFY_IMAGE_ATTRIBUTE_RESPONSE

    def register_image(self):
        if self.is_not_dryrun("RegisterImage"):
            raise NotImplementedError("AMIs.register_image is not yet implemented")

    def reset_image_attribute(self):
        if self.is_not_dryrun("ResetImageAttribute"):
            raise NotImplementedError(
                "AMIs.reset_image_attribute is not yet implemented"
            )


CREATE_IMAGE_RESPONSE = """<CreateImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
</CreateImageResponse>"""

COPY_IMAGE_RESPONSE = """<CopyImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>60bc441d-fa2c-494d-b155-5d6a3EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
</CopyImageResponse>"""

# TODO almost all of these params should actually be templated based on
# the ec2 image
DESCRIBE_IMAGES_RESPONSE = """<DescribeImagesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <imagesSet>
    {% for image in images %}
        <item>
          <imageId>{{ image.id }}</imageId>
          <imageLocation>{{ image.image_location }}</imageLocation>
          <imageState>{{ image.state }}</imageState>
          <imageOwnerId>{{ image.owner_id }}</imageOwnerId>
          <isPublic>{{ image.is_public_string }}</isPublic>
          <architecture>{{ image.architecture }}</architecture>
          <imageType>{{ image.image_type }}</imageType>
          <kernelId>{{ image.kernel_id }}</kernelId>
          <ramdiskId>ari-1a2b3c4d</ramdiskId>
          <imageOwnerAlias>amazon</imageOwnerAlias>
          <creationDate>{{ image.creation_date }}</creationDate>
          <name>{{ image.name }}</name>
          {% if image.platform %}
             <platform>{{ image.platform }}</platform>
          {% endif %}
          <description>{{ image.description }}</description>
          <rootDeviceType>{{ image.root_device_type }}</rootDeviceType>
          <rootDeviceName>{{ image.root_device_name }}</rootDeviceName>
          <blockDeviceMapping>
          {% for device in image.block_device_mapping %}
            <item>
              <deviceName>{{ device["device_name"] }}</deviceName>
              <ebs>
                <snapshotId>{{ image.ebs_snapshot.id }}</snapshotId>
                <volumeSize>{{ device["ebs"]["volume_size"] }}</volumeSize>
                <deleteOnTermination>{{ device["ebs"]["delete"] }}</deleteOnTermination>
                <volumeType>{{ device["ebs"]["volume_type"] }}</volumeType>
                {% if device["ebs"]["iops"] %}
                    <iops>{{ device["ebs"]["iops"] }}</iops>
                {% endif %}
              </ebs>
            </item>
          {% endfor %}  
          </blockDeviceMapping>
          <virtualizationType>{{ image.virtualization_type }}</virtualizationType>
          <tagSet>
            {% for tag in image.get_tags() %}
              <item>
                <resourceId>{{ tag.resource_id }}</resourceId>
                <resourceType>{{ tag.resource_type }}</resourceType>
                <key>{{ tag.key }}</key>
                <value>{{ tag.value }}</value>
              </item>
            {% endfor %}
          </tagSet>
          <hypervisor>xen</hypervisor>
        </item>
    {% endfor %}
  </imagesSet>
</DescribeImagesResponse>"""

DESCRIBE_IMAGE_RESPONSE = """<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
   <{{ key }}>
     <value>{{ value }}</value>
   </{{key }}>
</DescribeImageAttributeResponse>"""

DEREGISTER_IMAGE_RESPONSE = """<DeregisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>{{ success }}</return>
</DeregisterImageResponse>"""

DESCRIBE_IMAGE_ATTRIBUTES_RESPONSE = """
<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ ami_id }}</imageId>
   {% if not groups and not users %}
      <launchPermission/>
   {% else %}
      <launchPermission>
         {% if groups %}
            {% for group in groups %}
               <item>
                  <group>{{ group }}</group>
               </item>
            {% endfor %}
         {% endif %}
         {% if users %}
            {% for user in users %}
               <item>
                  <userId>{{ user }}</userId>
               </item>
            {% endfor %}
         {% endif %}
      </launchPermission>
   {% endif %}
</DescribeImageAttributeResponse>"""

MODIFY_IMAGE_ATTRIBUTE_RESPONSE = """
<ModifyImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <return>true</return>
</ModifyImageAttributeResponse>
"""
